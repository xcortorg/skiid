import React from 'react';
import { AlertCircle, Check, LogIn, Download, Copy, Send, X } from 'lucide-react';
import toast from 'react-hot-toast';

type NotificationType = 'success' | 'error' | 'info';
type NotificationIcon = 'check' | 'alert' | 'login' | 'download' | 'copy' | 'send';

interface NotificationProps {
  title: string;
  message: string;
  type?: NotificationType;
  icon?: NotificationIcon;
  duration?: number;
}

// Keep track of active notifications to prevent duplicates
const activeNotifications = new Set<string>();

const getIcon = (icon: NotificationIcon, type: NotificationType) => {
  const iconColor = type === 'success' ? 'text-green-500' : type === 'error' ? 'text-red-500' : 'text-theme';
  const iconClass = `h-10 w-10 ${iconColor} p-2`;

  switch (icon) {
    case 'check':
      return <Check className={iconClass} />;
    case 'alert':
      return <AlertCircle className={iconClass} />;
    case 'login':
      return <LogIn className={iconClass} />;
    case 'download':
      return <Download className={iconClass} />;
    case 'copy':
      return <Copy className={iconClass} />;
    case 'send':
      return <Send className={iconClass} />;
    default:
      return type === 'success' ? (
        <Check className={iconClass} />
      ) : type === 'error' ? (
        <AlertCircle className={iconClass} />
      ) : (
        <LogIn className={iconClass} />
      );
  }
};

export const showNotification = ({
  title,
  message,
  type = 'info',
  icon,
  duration = 3000
}: NotificationProps) => {
  // Create a unique key for this notification
  const notificationKey = `${title}-${message}`;

  // Check if this notification is already active
  if (activeNotifications.has(notificationKey)) {
    return;
  }

  // Add to active notifications
  activeNotifications.add(notificationKey);

  // Show the notification
  toast.custom(
    (t) => (
      <div className={`${t.visible ? 'animate-enter' : 'animate-leave'} max-w-md w-full bg-dark-2 shadow-lg rounded-lg pointer-events-auto flex ring-1 ring-black ring-opacity-5`}>
        <div className="flex-1 w-0 p-4">
          <div className="flex items-start">
            <div className="flex-shrink-0 pt-0.5">
              {getIcon(icon || (type === 'success' ? 'check' : type === 'error' ? 'alert' : 'login'), type)}
            </div>
            <div className="ml-3 flex-1">
              <p className="text-sm font-medium text-gray-100">{title}</p>
              <p className="mt-1 text-sm text-gray-400">{message}</p>
            </div>
          </div>
        </div>
        <div className="flex border-l border-dark-4">
          <button
            onClick={() => {
              toast.dismiss(t.id);
              // Remove from active notifications when dismissed
              activeNotifications.delete(notificationKey);
            }}
            className="w-full border border-transparent rounded-none rounded-r-lg p-4 flex items-center justify-center text-sm font-medium text-gray-400 hover:text-gray-300 focus:outline-none transition-colors duration-200 ease-in-out hover:bg-dark-3"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    ),
    {
      position: "top-right",
      duration: type === 'error' ? 5000 : duration,
      // Remove from active notifications when the toast expires
      onDismiss: () => {
        activeNotifications.delete(notificationKey);
      }
    }
  );
};

export default showNotification;