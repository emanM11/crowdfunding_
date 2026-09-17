export default function StarRating({ value, onRate, disabled }) {
  return (
    <div className="rating-row">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          className={`star-btn${star <= Math.round(value || 0) ? " filled" : ""}`}
          disabled={disabled}
          onClick={() => onRate?.(star)}
          aria-label={`${star} out of 5`}
        >
          ★
        </button>
      ))}
    </div>
  );
}
