'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  TrendingUp,
  BarChart3,
  Search,
  BookOpen,
  FlaskConical,
  Bot,
  Shield,
  Settings,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Options', href: '/options', icon: TrendingUp },
  { name: 'Indicators', href: '/indicators', icon: BarChart3 },
  { name: 'Scanner', href: '/scanner', icon: Search },
  { name: 'Journal', href: '/journal', icon: BookOpen },
  { name: 'Strategies', href: '/strategies', icon: FlaskConical },
  { name: 'AI Assistant', href: '/ai-assistant', icon: Bot },
  { name: 'Risk', href: '/risk', icon: Shield },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const [isCollapsed, setIsCollapsed] = useState(false);

  const handleToggle = useCallback(() => {
    setIsCollapsed(prev => !prev);
  }, []);

  return (
    <aside
      className={cn(
        'flex flex-col border-r bg-card transition-all duration-300',
        isCollapsed ? 'w-16' : 'w-64'
      )}
    >
      <div className="flex h-16 items-center justify-between border-b px-2 sm:px-4">
        {!isCollapsed && (
          <h1 className="text-base sm:text-lg font-bold tracking-tight truncate">
            AI Trading
          </h1>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={handleToggle}
          className="h-8 w-8"
        >
          {isCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>

      <nav className="flex-1 space-y-1 p-2 overflow-y-auto">
        {navigation.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
          const Icon = item.icon;

          const linkContent = (
            <Link
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              )}
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              {!isCollapsed && <span className="truncate">{item.name}</span>}
            </Link>
          );

          if (isCollapsed) {
            return (
              <Tooltip key={item.name} delayDuration={0}>
                <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
                <TooltipContent side="right">{item.name}</TooltipContent>
              </Tooltip>
            );
          }

          return <div key={item.name}>{linkContent}</div>;
        })}
      </nav>

      <div className="border-t p-2 sm:p-4">
        {!isCollapsed && (
          <div className="rounded-lg bg-accent p-2 sm:p-3">
            <p className="text-xs font-medium text-accent-foreground">
              Market Hours
            </p>
            <p className="text-base sm:text-lg font-bold">
              {new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })}
            </p>
            <p className="text-xs text-muted-foreground">IST (UTC+5:30)</p>
          </div>
        )}
      </div>
    </aside>
  );
}
