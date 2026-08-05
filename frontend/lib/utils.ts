import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(num: number, decimals: number = 2): string {
  return num.toFixed(decimals);
}

export function formatPercentage(num: number, decimals: number = 2): string {
  return `${num >= 0 ? '+' : ''}${num.toFixed(decimals)}%`;
}

export function formatCurrency(num: number, currency: string = 'INR'): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

export function formatCompactNumber(num: number): string {
  if (num >= 10000000) {
    return `${(num / 10000000).toFixed(2)}Cr`;
  }
  if (num >= 100000) {
    return `${(num / 100000).toFixed(2)}L`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(2)}K`;
  }
  return num.toString();
}

export function formatVolume(num: number): string {
  if (num >= 10000000) {
    return `${(num / 10000000).toFixed(2)} Cr`;
  }
  if (num >= 100000) {
    return `${(num / 100000).toFixed(2)} L`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(2)} K`;
  }
  return num.toString();
}

export function formatDate(date: Date | string, format: 'short' | 'long' | 'time' = 'short'): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  
  switch (format) {
    case 'long':
      return d.toLocaleDateString('en-IN', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    case 'time':
      return d.toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'Asia/Kolkata',
      });
    default:
      return d.toLocaleDateString('en-IN');
  }
}

export function getPriceChangeColor(change: number): string {
  if (change > 0) return 'text-green-600';
  if (change < 0) return 'text-red-600';
  return 'text-gray-600';
}

export function getPriceChangeClass(change: number): string {
  if (change > 0) return 'bg-green-500/10 text-green-600';
  if (change < 0) return 'bg-red-500/10 text-red-600';
  return 'bg-gray-500/10 text-gray-600';
}

export function calculateChangePercent(current: number, previous: number): number {
  if (previous === 0) return 0;
  return ((current - previous) / previous) * 100;
}

export function calculatePnL(entry: number, exit: number, quantity: number, type: 'long' | 'short'): number {
  if (type === 'long') {
    return (exit - entry) * quantity;
  }
  return (entry - exit) * quantity;
}

export function calculateRiskReward(entry: number, stopLoss: number, target: number, type: 'long' | 'short'): number {
  const risk = type === 'long' ? entry - stopLoss : stopLoss - entry;
  const reward = type === 'long' ? target - entry : entry - target;
  return reward / risk;
}

export function getIndianMarketStatus(): 'open' | 'closed' | 'pre_market' | 'post_market' {
  const now = new Date();
  const istTime = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const hours = istTime.getHours();
  const minutes = istTime.getMinutes();
  const day = istTime.getDay();
  
  // Weekend
  if (day === 0 || day === 6) return 'closed';
  
  const currentTime = hours * 60 + minutes;
  const marketOpen = 9 * 60 + 15; // 9:15 AM
  const marketClose = 15 * 60 + 30; // 3:30 PM
  const preMarketOpen = 9 * 60; // 9:00 AM
  const postMarketClose = 17 * 60; // 5:00 PM
  
  if (currentTime >= preMarketOpen && currentTime < marketOpen) return 'pre_market';
  if (currentTime >= marketOpen && currentTime <= marketClose) return 'open';
  if (currentTime > marketClose && currentTime <= postMarketClose) return 'post_market';
  
  return 'closed';
}

export function getNextExpiry(): string {
  const now = new Date();
  const thursday = 4;
  let daysUntilThursday = (thursday - now.getDay() + 7) % 7;
  if (daysUntilThursday === 0) {
    const thursdayDate = new Date(now);
    thursdayDate.setDate(now.getDate() + 7);
    return thursdayDate.toISOString().split('T')[0];
  }
  const nextThursday = new Date(now);
  nextThursday.setDate(now.getDate() + daysUntilThursday);
  return nextThursday.toISOString().split('T')[0];
}

export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;
  
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

export function throttle<T extends (...args: unknown[]) => unknown>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean;
  
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}
