import toast, { Toaster } from 'react-hot-toast';

export function ToastContainer() {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 3000,
        style: {
          background: '#1e293b',
          color: '#f8fafc',
          fontSize: '13px',
          borderRadius: '12px',
          padding: '12px 16px',
        },
        success: {
          iconTheme: { primary: '#10b981', secondary: '#fff' },
        },
        error: {
          iconTheme: { primary: '#ef4444', secondary: '#fff' },
        },
      }}
    />
  );
}

export function notifySuccess(message) {
  toast.success(message);
}

export function notifyError(message) {
  toast.error(message);
}

export function notifyInfo(message) {
  toast(message);
}
