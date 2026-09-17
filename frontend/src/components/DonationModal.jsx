import { useEffect, useMemo, useRef, useState } from "react";

import { CardElement, Elements, useElements, useStripe } from "@stripe/react-stripe-js";

import { loadStripe } from "@stripe/stripe-js";

import { CheckCircle2, CreditCard, Loader2, Lock, ShieldCheck, X, XCircle } from "lucide-react";

import { confirmDonation, getPaymentGatewayConfig, processDonation } from "../api/payments";

import { notifySuccess } from "../lib/toast";

const QUICK_AMOUNTS = [100, 250, 500, 1000, 2500];

const CURRENCY_SYMBOLS = { EGP: "EGP", USD: "$" };

const STRIPE_ERRORS = {

  card_declined: "The card was declined by the issuing bank. Try another card or contact your bank.",

  insufficient_funds: "The card has insufficient funds to complete this transaction.",

  expired_card: "The card has expired.",

  incorrect_cvc: "The CVC code is incorrect.",

  incorrect_number: "The card number is incorrect.",

  invalid_number: "The card number is incorrect.",

  invalid_expiry_month: "The expiration month is invalid.",

  invalid_expiry_year: "The expiration year is invalid.",

  processing_error: "An error occurred while processing the payment. Please try again.",

  authentication_required: "Bank security verification is required (3D Secure) — follow the authentication steps.",

  rate_limit: "Too many requests — please wait a moment and try again.",

  gateway_unavailable: "The payment gateway is currently unavailable. Please try again later.",

  network: "Unable to reach the payment server. Check your internet connection and try again.",

};

const CARD_ELEMENT_OPTIONS = {

  hidePostalCode: true,

  style: {

    base: {

      fontSize: "15px",

      color: "#0b1b2b",

      "::placeholder": { color: "#97a3b5" },

    },

    invalid: { color: "#dc2626" },

  },

};

function digitsOnly(value) {

  return (value || "").replace(/[\s-]/g, "");

}

function isLuhnValid(number) {

  let sum = 0;

  for (let i = 0; i < number.length; i++) {

    let d = Number(number[number.length - 1 - i]);

    if (i % 2 === 1) {

      d *= 2;

      if (d > 9) d -= 9;

    }

    sum += d;

  }

  return sum % 10 === 0;

}

function cardBrand(number) {

  const n = digitsOnly(number);

  if (/^4/.test(n)) return "visa";

  if (/^(5[1-5]|2[2-7])/.test(n)) return "mastercard";

  if (/^3[47]/.test(n)) return "amex";

  if (/^6[01]|^65/.test(n)) return "discover";

  return "";

}

function formatCardNumber(value) {

  return digitsOnly(value)

    .slice(0, 16)

    .replace(/(\d{4})(?=\d)/g, "$1 ");

}

// Strict MM/YY mask: only digits survive, the slash is inserted exactly

// after the two month digits and never left hanging (no "22///").

function formatExpiry(value) {

  const digits = String(value).replace(/\D/g, "").slice(0, 4);

  if (!digits) return "";

  if (digits.length <= 2) return digits;

  return `${digits.slice(0, 2)}/${digits.slice(2)}`;

}

function expiryParts(expiry) {

  const match = (expiry || "").match(/^(\d{2})\/(\d{2})$/);

  if (!match) return null;

  return { month: Number(match[1]), year: 2000 + Number(match[2]) };

}

function isMonthInvalid(expiry) {

  const parts = expiryParts(expiry);

  return parts ? parts.month < 1 || parts.month > 12 : false;

}

function isExpired(expiry) {

  const parts = expiryParts(expiry);

  if (!parts) return false;

  const now = new Date();

  return parts.year < now.getFullYear() || (parts.year === now.getFullYear() && parts.month < now.getMonth() + 1);

}

function newIdempotencyKey() {

  return typeof crypto !== "undefined" && crypto.randomUUID

    ? crypto.randomUUID()

    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

}

function apiErrorMessage(err) {

  const code = err.response?.data?.error_code;

  if (code && STRIPE_ERRORS[code]) return STRIPE_ERRORS[code];

  if (err?.code === "ERR_NETWORK" || /network/i.test(err?.message || "")) return STRIPE_ERRORS.network;

  return err.response?.data?.detail || "The transaction was declined. Please try again or use another card.";

}

function stripeErrorMessage(code, type, rawMessage) {

  if (code && STRIPE_ERRORS[code]) return STRIPE_ERRORS[code];

  if (type === "card_error" && /invalid_expiry/i.test(code || "")) return STRIPE_ERRORS.invalid_expiry_month;

  if (rawMessage && /[a-z]/i.test(rawMessage) && rawMessage.length < 90) return rawMessage;

  return "An error occurred while processing the payment. Please try again.";

}

function BrandMarks() {

  return (

    <div className="brand-marks" aria-hidden="true">

      {["visa", "mastercard", "amex", "discover"].map((name) => (

        <span key={name} className={`brand-mark brand-mark-${name}`}>

          {name === "visa" && "VISA"}

          {name === "mastercard" && "mastercard"}

          {name === "amex" && "AMEX"}

          {name === "discover" && "DISC"}

        </span>

      ))}

    </div>

  );

}

function SecureBadge() {

  return (

    <div className="secure-badge">

      <Lock size={13} />

      <span className="secure-badge-title">256-bit SSL Encryption</span>

      <span className="secure-badge-dot" />

      <ShieldCheck size={13} />

      <span>Your data is encrypted and never reaches us</span>

    </div>

  );

}

function StripeCardForm({ projectId, amount, currency, isAnonymous, holder, onStart, onSuccess, onFail }) {

  const stripe = useStripe();

  const elements = useElements();

  const submit = async () => {

    if (!stripe || !elements) return;

    onStart();

    try {

      const { data: intent } = await processDonation(projectId, {

        amount: Number(amount).toFixed(2),

        currency,

        is_anonymous: isAnonymous,

        cardholder_name: holder.trim(),

        idempotency_key: newIdempotencyKey(),

      });

      const { error: confirmError } = await stripe.confirmCardPayment(intent.client_secret, {

        payment_method: {

          card: elements.getElement(CardElement),

          billing_details: { name: holder.trim() },

        },

      });

      if (confirmError) {

        onFail(

          stripeErrorMessage(confirmError.code, confirmError.type, confirmError.message),

          confirmError.code || "payment_failed"

        );

        return;

      }

      const { data: donation } = await confirmDonation(projectId, intent.payment_intent_id);

      onSuccess(donation);

    } catch (err) {

      onFail(apiErrorMessage(err), err.response?.data?.error_code || "");

    }

  };

  return (

    <>

      <div className="stripe-element-wrap">

        <CardElement options={CARD_ELEMENT_OPTIONS} />

      </div>

      <button className="btn btn-primary btn-block" onClick={submit} disabled={!stripe || !elements}>

        Complete Secure Payment

        <ShieldCheck size={15} />

      </button>

    </>

  );

}

export default function DonationModal({ open, projectId, projectTitle, initialAmount, onClose, onSuccess }) {

  // step: checking | amount | card | processing | success | failed

  const [step, setStep] = useState(initialAmount ? "checking" : "amount");

  const [amount, setAmount] = useState(initialAmount ? String(initialAmount) : "");

  const [currency, setCurrency] = useState("EGP");

  const [isAnonymous, setIsAnonymous] = useState(false);

  const [holder, setHolder] = useState("");

  const [cardNumber, setCardNumber] = useState("");

  const [expiry, setExpiry] = useState("");

  const [cvc, setCvc] = useState("");

  const [fieldErrors, setFieldErrors] = useState({});

  const [result, setResult] = useState(null);

  const [gateway, setGateway] = useState(null);

  const [gatewayError, setGatewayError] = useState("");

  const holderRef = useRef(null);

  const stripePromise = useMemo(

    () => (import.meta.env.VITE_STRIPE_PUBLIC_KEY ? loadStripe(import.meta.env.VITE_STRIPE_PUBLIC_KEY) : null),

    []

  );

  useEffect(() => {

    if (!open) return;

    setStep(initialAmount ? "checking" : "amount");

    setAmount(initialAmount ? String(initialAmount) : "");

    setCurrency("EGP");

    setIsAnonymous(false);

    setHolder("");

    setCardNumber("");

    setExpiry("");

    setCvc("");

    setFieldErrors({});

    setResult(null);

    setGateway(null);

    setGatewayError("");

    getPaymentGatewayConfig()

      .then(({ data }) => setGateway(data.gateway))

      .catch(() => setGatewayError("Unable to verify the payment gateway. Check your internet connection and try again."));

  }, [open, initialAmount]);

  useEffect(() => {

    if (step === "checking" && gateway) {

      setStep("card");

      setTimeout(() => holderRef.current?.focus(), 50);

    }

    if (step === "checking" && gatewayError) {

      setStep("amount");

    }

  }, [step, gateway, gatewayError]);

  if (!open) return null;

  const symbol = CURRENCY_SYMBOLS[currency] || "EGP";

  const brand = cardBrand(cardNumber);

  const validateAmount = () => {

    const value = Number(amount);

    if (!amount || !Number.isFinite(value) || value <= 0) {

      setFieldErrors({ amount: "Enter a valid amount greater than zero." });

      return false;

    }

    setFieldErrors({});

    return true;

  };

  const validateCard = () => {

    const errors = {};

    if (digitsOnly(cardNumber).length < 13 || !isLuhnValid(digitsOnly(cardNumber))) {

      errors.number = "The card number is incorrect.";

    }

    if (!/^(\d{2})\/(\d{2})$/.test(expiry)) {

      errors.expiry = "Enter the expiration date in MM/YY format.";

    } else if (isMonthInvalid(expiry)) {

      errors.expiry = "The expiration month must be between 01 and 12.";

    } else if (isExpired(expiry)) {

      errors.expiry = "The card has expired.";

    }

    if (!/^\d{3,4}$/.test(cvc)) {

      errors.cvc = "CVC must be 3 or 4 digits.";

    }

    setFieldErrors(errors);

    return Object.keys(errors).length === 0;

  };

  const goToCard = () => {

    if (!validateAmount()) return;

    if (gatewayError) setGatewayError("");

    if (!gateway) {

      setStep("checking");

      return;

    }

    setStep("card");

    setTimeout(() => holderRef.current?.focus(), 50);

  };

  const finishSuccess = (donation) => {

    setResult({ ok: true, donation });

    setStep("success");

    notifySuccess(`Donation of ${Number(donation.amount ?? amount).toLocaleString("en-US")} ${symbol} completed successfully!`);

    onSuccess?.();

  };

  const finishFail = (message, errorCode) => {

    setResult({ ok: false, message, error_code: errorCode });

    setStep("failed");

  };

  const submitMock = async () => {

    if (!validateCard()) return;

    setStep("processing");

    try {

      const { data } = await processDonation(projectId, {

        amount: Number(amount).toFixed(2),

        currency,

        is_anonymous: isAnonymous,

        cardholder_name: holder.trim(),

        card_number: digitsOnly(cardNumber),

        card_expiry: expiry,

        card_cvc: cvc,

        idempotency_key: newIdempotencyKey(),

      });

      finishSuccess(data);

    } catch (err) {

      finishFail(apiErrorMessage(err), err.response?.data?.error_code || "");

    }

  };

  const renderCardStep = () => {

    if (gateway === "stripe") {

      if (!stripePromise) {

        return (

          <div className="modal-center">

            <ShieldCheck size={34} className="result-icon failed" />

            <h3>Secure Payment Is Not Enabled</h3>

            <p>The payment gateway is not ready on this server yet. Please try again later or use a supported currency.</p>

            <button className="modal-back" onClick={onClose}>

              Close

            </button>

          </div>

        );

      }

      return (

        <Elements stripe={stripePromise}>

          <StripeCardForm

            projectId={projectId}

            amount={amount}

            currency={currency}

            isAnonymous={isAnonymous}

            holder={holder}

            onStart={() => setStep("processing")}

            onSuccess={finishSuccess}

            onFail={finishFail}

          />

        </Elements>

      );

    }

    return (

      <>

        <div className="field">

          <label>Card Number</label>

          <div className={`card-input-wrap ${fieldErrors.number ? "is-error" : ""}`}>

            <input

              className="input"

              dir="ltr"

              inputMode="numeric"

              autoComplete="cc-number"

              placeholder="0000 0000 0000 0000"

              value={cardNumber}

              onChange={(e) => setCardNumber(formatCardNumber(e.target.value))}

            />

            {brand && <span className={`card-brand card-brand-${brand}`}>{brand}</span>}

          </div>

          {fieldErrors.number && <p className="field-error">{fieldErrors.number}</p>}

        </div>

        <div className="split-fields">

          <div className="field">

            <label>Expiration Date</label>

            <input

              className={`input ${fieldErrors.expiry ? "has-error" : ""}`}

              dir="ltr"

              inputMode="numeric"

              autoComplete="cc-exp"

              placeholder="MM/YY"

              value={expiry}

              onChange={(e) => setExpiry(formatExpiry(e.target.value))}

            />

            {fieldErrors.expiry && <p className="field-error">{fieldErrors.expiry}</p>}

          </div>

          <div className="field">

            <label>CVC</label>

            <input

              className={`input ${fieldErrors.cvc ? "has-error" : ""}`}

              dir="ltr"

              inputMode="numeric"

              autoComplete="cc-csc"

              placeholder="123"

              maxLength={4}

              value={cvc}

              onChange={(e) => setCvc(e.target.value.replace(/\D/g, "").slice(0, 4))}

            />

            {fieldErrors.cvc && <p className="field-error">{fieldErrors.cvc}</p>}

          </div>

        </div>

        <button className="btn btn-primary btn-block" onClick={submitMock}>

          Complete Payment

          <ShieldCheck size={15} />

        </button>

      </>

    );

  };

  return (

    <div className="modal-overlay" role="dialog" aria-modal="true">

      <div className={`modal modal-${step}`} dir="rtl">

        <div className="modal-head">

          <div className="modal-title">

            <CreditCard size={18} />

            <span>Secure Payment</span>

          </div>

          {step !== "processing" && (

            <button className="modal-close" onClick={onClose} aria-label="Close">

              <X size={18} />

            </button>

          )}

        </div>

        {step === "checking" && (

          <div className="modal-body modal-center">

            <Loader2 className="spinner" size={38} />

            <p>Preparing the secure payment gateway...</p>

          </div>

        )}

        {step === "amount" && (

          <div className="modal-body">

            <p className="modal-subtitle">

              Support {projectTitle || "the project"} — choose the amount and currency.

            </p>

            {gatewayError && <p className="field-error">{gatewayError}</p>}

            <div className="field">

              <label>Donation Amount ({symbol})</label>

              <div className="amount-input-row">

                <input

                  className={`input ${fieldErrors.amount ? "has-error" : ""}`}

                  type="number"

                  min="1"

                  step="0.01"

                  placeholder="0.00"

                  value={amount}

                  onChange={(e) => setAmount(e.target.value)}

                />

                <select

                  className="input"

                  value={currency}

                  onChange={(e) => setCurrency(e.target.value)}

                  style={{ width: 110 }}

                >

                  <option value="EGP">EGP</option>

                  <option value="USD">$</option>

                </select>

              </div>

              {fieldErrors.amount && <p className="field-error">{fieldErrors.amount}</p>}

              <div className="category-pills" style={{ marginTop: 8, gap: 6 }}>

                {QUICK_AMOUNTS.map((q) => (

                  <button

                    key={q}

                    type="button"

                    className="category-pill"

                    style={{

                      padding: "6px 12px",

                      fontSize: "0.8rem",

                      cursor: "pointer",

                      background: Number(amount) === q ? "var(--navy-900)" : undefined,

                      color: Number(amount) === q ? "#fff" : undefined,

                    }}

                    onClick={() => setAmount(String(q))}

                  >

                    <bdi>{q}</bdi>

                  </button>

                ))}

              </div>

            </div>

            <label className="checkbox-row">

              <input

                type="checkbox"

                checked={isAnonymous}

                onChange={(e) => setIsAnonymous(e.target.checked)}

              />

              <span>Donate anonymously — your donation will not appear under your name in the project history.</span>

            </label>

            <button className="btn btn-primary btn-block" onClick={goToCard}>

              Pay by Card

              <Lock size={15} />

            </button>

            <SecureBadge />

          </div>

        )}

        {step === "card" && (

          <div className="modal-body">

            <p className="modal-subtitle">

              <bdi>{Number(amount).toLocaleString("en-US")}</bdi> {symbol} — for {projectTitle}

            </p>

            {gateway === "mock" && (

              <div className="field">

                <label>Accepted Cards</label>

                <BrandMarks />

              </div>

            )}

            <div className="field">

              <label>Cardholder Name {gateway === "stripe" && "(Optional)"}</label>

              <input

                ref={holderRef}

                className={`input ${fieldErrors.holder ? "has-error" : ""}`}

                placeholder="AS SHOWN ON CARD"

                dir="ltr"

                autoComplete="cc-name"

                value={holder}

                onChange={(e) => setHolder(e.target.value)}

              />

              {fieldErrors.holder && <p className="field-error">{fieldErrors.holder}</p>}

            </div>

            {renderCardStep()}

            <SecureBadge />

            <button className="modal-back" onClick={() => setStep("amount")}>

              Back to Edit Amount

            </button>

          </div>

        )}

        {step === "processing" && (

          <div className="modal-body modal-center">

            <Loader2 className="spinner" size={38} />

            <p>{gateway === "stripe" ? "Confirming secure payment..." : "Processing payment..."}</p>

            <p className="hint">Please do not close the page — the transaction is fully encrypted and secured.</p>

          </div>

        )}

        {step === "success" && (

          <div className="modal-body modal-center">

            <CheckCircle2 className="result-icon success" size={40} />

            <h3>Donation Successful</h3>

            <p>

              Thank you for your support of{" "}

              <bdi>{Number(result?.donation?.amount ?? amount).toLocaleString("en-US")}</bdi>{" "}

              {result?.donation?.currency ? CURRENCY_SYMBOLS[result.donation.currency] || "EGP" : symbol}

            </p>

            {result?.donation?.payment_method && (

              <p className="hint">

                Paid with {result.donation.payment_method}

              </p>

            )}

            {result?.donation?.transaction_id && (

              <div className="ref-box" dir="ltr">

                Transaction ID: <bdi>{result.donation.transaction_id}</bdi>

              </div>

            )}

            <button className="btn btn-primary btn-block" onClick={onClose}>

              Done

            </button>

          </div>

        )}

        {step === "failed" && (

          <div className="modal-body modal-center">

            <XCircle className="result-icon failed" size={40} />

            <h3>Payment Failed</h3>

            <p>{result?.message}</p>

            {result?.error_code && (

              <p className="hint" dir="ltr">

                <bdi>{result.error_code}</bdi>

              </p>

            )}

            <button

              className="btn btn-primary btn-block"

              onClick={() => {

                setFieldErrors({});

                setStep("card");

              }}

            >

              Try Again

            </button>

            <button className="modal-back" onClick={onClose}>

              Cancel

            </button>

          </div>

        )}

      </div>

    </div>

  );

}