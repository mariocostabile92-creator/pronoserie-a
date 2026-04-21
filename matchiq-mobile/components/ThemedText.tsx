import { Text, type TextProps, StyleSheet } from 'react-native';
import { Colors, Typography } from '../constants/theme';

export type ThemedTextProps = TextProps & {
  type?: 'h1' | 'h2' | 'h3' | 'body' | 'caption' | 'small';
  color?: 'primary' | 'secondary' | 'muted' | 'accent' | 'danger';
};

export function ThemedText({ style, type = 'body', color = 'primary', ...rest }: ThemedTextProps) {
  const colorStyles = {
    primary: { color: Colors.text },
    secondary: { color: Colors.textSecondary },
    muted: { color: Colors.textMuted },
    accent: { color: Colors.accent },
    danger: { color: Colors.danger },
  };

  return (
    <Text
      style={[
        styles[type],
        colorStyles[color],
        style,
      ]}
      {...rest}
    />
  );
}

const styles = StyleSheet.create({
  h1: { ...Typography.h1 },
  h2: { ...Typography.h2 },
  h3: { ...Typography.h3 },
  body: { ...Typography.body },
  caption: { ...Typography.caption },
  small: { ...Typography.small },
});
