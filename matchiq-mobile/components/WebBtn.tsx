/**
 * WebBtn - Bottone stile webapp: border-radius 24px, variante green/blue
 */
import React from 'react';
import {
  TouchableOpacity,
  Text,
  ViewStyle,
  TextStyle,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { Colors } from '../constants/theme';

interface WebBtnProps {
  label: string;
  onPress: () => void;
  variant?: 'green' | 'blue' | 'outline';
  style?: ViewStyle;
  textStyle?: TextStyle;
  loading?: boolean;
  disabled?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function WebBtn({
  label,
  onPress,
  variant = 'green',
  style,
  textStyle,
  loading = false,
  disabled = false,
  size = 'md',
}: WebBtnProps) {
  const bg = variant === 'green' ? Colors.green
    : variant === 'blue' ? Colors.accent
    : 'transparent';
  const textColor = variant === 'outline' ? Colors.accent : (variant === 'green' ? '#000' : '#fff');
  const padH = size === 'sm' ? 16 : size === 'lg' ? 40 : 28;
  const padV = size === 'sm' ? 8 : size === 'lg' ? 16 : 12;
  const fontSize = size === 'sm' ? 13 : size === 'lg' ? 17 : 15;

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled || loading}
      style={[
        styles.btn,
        {
          backgroundColor: bg,
          paddingHorizontal: padH,
          paddingVertical: padV,
          opacity: disabled ? 0.5 : 1,
          borderWidth: variant === 'outline' ? 1 : 0,
          borderColor: Colors.accent,
        },
        style,
      ]}
      activeOpacity={0.75}
    >
      {loading ? (
        <ActivityIndicator color={textColor} size="small" />
      ) : (
        <Text style={[styles.btnText, { color: textColor, fontSize }, textStyle]}>
          {label}
        </Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  btn: {
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 44,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 3,
  },
  btnText: {
    fontWeight: '700',
  },
});
