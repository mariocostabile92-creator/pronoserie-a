/**
 * Card - Stile identico alla webapp: background #162447, border #1f3460, border-radius 14px
 */
import React from 'react';
import { View, ViewStyle, StyleSheet } from 'react-native';
import { Colors } from '../constants/theme';

interface CardProps {
  children: React.ReactNode;
  style?: ViewStyle | ViewStyle[];
  highlight?: 'green' | 'blue' | 'yellow' | 'red';
}

export function Card({ children, style, highlight }: CardProps) {
  const borderColor = highlight === 'green' ? Colors.green
    : highlight === 'blue' ? Colors.accent
    : highlight === 'yellow' ? Colors.yellow
    : highlight === 'red' ? Colors.red
    : Colors.border;

  return (
    <View style={[styles.card, { borderColor }, style]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: Colors.card,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: Colors.border,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 3,
  },
});
