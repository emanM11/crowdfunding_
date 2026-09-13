import toast from "react-hot-toast";

export function notifySuccess(message) {
  toast.success(message);
}

export function notifyError(message) {
  toast.error(message || "حصل خطأ غير متوقع.");
}

export function notify(message) {
  toast(message);
}