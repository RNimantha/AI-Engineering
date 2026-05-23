export type NavItem = {
  label: string;
  active?: boolean;
};

export type SalesRow = {
  month: string;
  sales: string;
  growth: string;
  forecast: string;
};

export const navItems: NavItem[] = [
  { label: "Dashboard" },
  { label: "Projects", active: true },
  { label: "Data Sources" },
  { label: "Agent Library" },
  { label: "API Keys" },
  { label: "Settings" },
];

export const salesRows: SalesRow[] = [
  { month: "2026-Q1", sales: "$21,900", growth: "6.8%", forecast: "92.1%" },
  { month: "2026-Q2", sales: "$23,100", growth: "7.2%", forecast: "96.4%" },
  { month: "2026-Q3", sales: "$25,980", growth: "9.1%", forecast: "104.8%" },
  { month: "2026-Q4", sales: "$28,120", growth: "8.4%", forecast: "108.0%" },
];
