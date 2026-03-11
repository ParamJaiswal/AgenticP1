import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface StatsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: { value: number; positive?: boolean };
  className?: string;
  iconColor?: string;
}

export function StatsCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  className,
  iconColor = "text-accent",
}: StatsCardProps) {
  return (
    <div className={cn("bg-white rounded-xl border border-gray-100 shadow-sm p-6", className)}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
          {trend && (
            <p
              className={cn(
                "text-xs font-medium mt-2",
                trend.positive !== false ? "text-green-600" : "text-red-600"
              )}
            >
              {trend.positive !== false ? "↑" : "↓"} {Math.abs(trend.value)}%{" "}
              <span className="text-gray-400">vs last month</span>
            </p>
          )}
        </div>
        <div className={cn("p-3 rounded-xl bg-gray-50", iconColor)}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}
