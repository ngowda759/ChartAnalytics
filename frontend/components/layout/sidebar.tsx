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
  X,
  LayoutGrid,
  Zap,
  Users,
  Fish,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Scan Dashboard', href: '/scan-dashboard', icon: LayoutGrid },
  { name: 'Options', href: '/options', icon: TrendingUp },
  { name: 'Indicators', href: '/indicators', icon: BarChart3 },
  { name: 'Scanner', href: '/scanner', icon: Search },
  { name: 'Journal', href: '/journal', icon: BookOpen },
  { name: 'Strategies', href: '/strategies', icon: FlaskConical },
  { name: 'Decision Signals', href: '/decision-signals', icon: Zap },
  { name: 'Predictions', href: '/predictions', icon: Fish },
  { name: 'AI Assistant', href: '/ai-assistant', icon: Bot },
  { name: 'Agent Analysis', href: '/agent-analysis', icon: Users },
  { name: 'Risk', href: '/risk', icon: Shield },
  { name: 'Settings', href: '/settings', icon: Settings },
];

interface SidebarProps {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
}

export function Sidebar({ isOpen, setIsOpen }: SidebarProps) {
  const pathname = usePathname();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  // The IST clock differs between server render and client hydration (time
  // advances ~1s), which triggers a React hydration mismatch warning. Render
  // a stable placeholder until mounted so server and client HTML match.
  const [clock, setClock] = useState<string | null>(null);

  useEffect(() => {
    const tick = () =>
      setClock(new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' }));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
      if (window.innerWidth < 768) {
        setIsCollapsed(false);
      }
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleNavClick = () => {
    if (isMobile) {
      setIsOpen(false);
    }
  };

  if (isMobile) {
    return (
      <>
        {/* Mobile overlay */}
        {isOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/50 md:hidden"
            onClick={() => setIsOpen(false)}
          />
        )}
        
        {/* Mobile sidebar drawer */}
        <aside
          className={cn(
            'fixed left-0 top-0 z-50 flex h-full w-64 flex-col border-r bg-card transition-transform duration-300 md:hidden',
            isOpen ? 'translate-x-0' : '-translate-x-full'
          )}
        >
          <div className="flex h-16 items-center justify-between border-b px-4">
            <h1 className="text-lg font-bold tracking-tight">AI Trading</h1>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsOpen(false)}
              className="h-8 w-8"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          <nav className="flex-1 space-y-1 p-2">
            {navigation.map((item) => {
              const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
              const Icon = item.icon;

              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={handleNavClick}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                  )}
                >
                  <Icon className="h-5 w-5 flex-shrink-0" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>

          <div className="border-t p-4">
            <div className="rounded-lg bg-accent p-3">
              <p className="text-xs font-medium text-accent-foreground">
                Market Hours
              </p>
              <p className="mt-1 text-lg font-bold">
                {clock ?? '—'}
              </p>
              <p className="text-xs text-muted-foreground">IST (UTC+5:30)</p>
            </div>
          </div>
        </aside>
      </>
    );
  }

  // Desktop sidebar
  return (
    <aside
      className={cn(
        'flex flex-col border-r bg-card transition-all duration-300',
        isCollapsed ? 'w-16' : 'w-64'
      )}
    >
      <div className="flex h-16 items-center justify-between border-b px-4">
        {!isCollapsed && (
          <h1 className="text-lg font-bold tracking-tight">
            AI Trading
          </h1>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="h-8 w-8"
        >
          {isCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>

      <nav className="flex-1 space-y-1 p-2">
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
              {!isCollapsed && <span>{item.name}</span>}
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

      <div className="border-t p-4">
        {!isCollapsed && (
          <div className="rounded-lg bg-accent p-3">
            <p className="text-xs font-medium text-accent-foreground">
              Market Hours
            </p>
            <p className="mt-1 text-lg font-bold">
              {clock ?? '—'}
            </p>
            <p className="text-xs text-muted-foreground">IST (UTC+5:30)</p>
          </div>
        )}
      </div>
    </aside>
  );
}
