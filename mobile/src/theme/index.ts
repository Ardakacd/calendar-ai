export const Colors = {
  primary: '#6366F1',
  primaryLight: '#EEF2FF',
  primaryDark: '#4F46E5',
  background: '#F8F9FB',
  surface: '#FFFFFF',
  textPrimary: '#111827',
  textSecondary: '#6B7280',
  textTertiary: '#9CA3AF',
  border: '#E5E7EB',
  borderLight: '#F3F4F6',
  error: '#EF4444',
  success: '#10B981',
  warning: '#F59E0B',
};

export const CategoryColors: Record<string, { accent: string; bg: string; text: string }> = {
  work:     { accent: '#6366F1', bg: '#EEF2FF', text: '#4338CA' },
  personal: { accent: '#A855F7', bg: '#FAF5FF', text: '#7E22CE' },
  health:   { accent: '#10B981', bg: '#ECFDF5', text: '#065F46' },
  social:   { accent: '#F59E0B', bg: '#FFFBEB', text: '#92400E' },
  default:  { accent: '#9CA3AF', bg: '#F9FAFB', text: '#6B7280' },
};

export function getCategoryColor(category?: string) {
  return CategoryColors[category ?? ''] ?? CategoryColors.default;
}

export const Radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  full: 9999,
};

export const Shadow = {
  sm: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  md: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 4,
  },
};
