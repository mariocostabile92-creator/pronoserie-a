import { View, type ViewProps, StyleSheet } from 'react-native';
import { Colors } from '../constants/theme';

export type ThemedViewProps = ViewProps & {
  variant?: 'default' | 'card' | 'surface';
};

export function ThemedView({ style, variant = 'default', ...rest }: ThemedViewProps) {
  const variantStyles = {
    default: styles.default,
    card: styles.card,
    surface: styles.surface,
  };

  return (
    <View
      style={[
        variantStyles[variant],
        style,
      ]}
      {...rest}
    />
  );
}

const styles = StyleSheet.create({
  default: {
    backgroundColor: Colors.background,
  },
  card: {
    backgroundColor: Colors.surface,
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  surface: {
    backgroundColor: Colors.surfaceLight,
    borderRadius: 8,
    padding: 12,
  },
});
