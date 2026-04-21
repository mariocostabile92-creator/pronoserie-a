import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Spacing, Typography, BorderRadius } from '../../constants/theme';
import { useAuth } from '../../contexts/AuthContext';

export default function LoginScreen() {
  const router = useRouter();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mostraPassword, setMostraPassword] = useState(false);
  const [caricamento, setCaricamento] = useState(false);
  const [errore, setErrore] = useState('');

  // Invia il form di login e gestisce risposta/errori
  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      setErrore('Inserisci email e password.');
      return;
    }
    try {
      setErrore('');
      setCaricamento(true);
      await login(email.trim(), password.trim());
      // La navigazione avviene automaticamente tramite _layout.tsx (token presente)
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        'Credenziali errate. Riprova.';
      setErrore(msg);
    } finally {
      setCaricamento(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {/* Logo / intestazione */}
        <View style={styles.header}>
          <View style={styles.logoContainer}>
            <Ionicons name="football" size={48} color={Colors.primary} />
          </View>
          <Text style={styles.title}>MatchIQ</Text>
          <Text style={styles.subtitle}>Accedi al tuo account</Text>
        </View>

        {/* Form di accesso */}
        <View style={styles.form}>
          {/* Messaggio di errore */}
          {errore !== '' && (
            <View style={styles.errorBox}>
              <Ionicons name="alert-circle" size={16} color={Colors.error} />
              <Text style={styles.errorText}>{errore}</Text>
            </View>
          )}

          {/* Campo email */}
          <View style={styles.inputWrapper}>
            <Text style={styles.label}>Email</Text>
            <View style={styles.inputContainer}>
              <Ionicons name="mail-outline" size={20} color={Colors.textMuted} style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="La tua email"
                placeholderTextColor={Colors.textMuted}
                value={email}
                onChangeText={setEmail}
                autoCapitalize="none"
                keyboardType="email-address"
                autoCorrect={false}
              />
            </View>
          </View>

          {/* Campo password */}
          <View style={styles.inputWrapper}>
            <Text style={styles.label}>Password</Text>
            <View style={styles.inputContainer}>
              <Ionicons name="lock-closed-outline" size={20} color={Colors.textMuted} style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="La tua password"
                placeholderTextColor={Colors.textMuted}
                value={password}
                onChangeText={setPassword}
                secureTextEntry={!mostraPassword}
                autoCapitalize="none"
              />
              <TouchableOpacity onPress={() => setMostraPassword(!mostraPassword)} style={styles.eyeButton}>
                <Ionicons
                  name={mostraPassword ? 'eye-off-outline' : 'eye-outline'}
                  size={20}
                  color={Colors.textMuted}
                />
              </TouchableOpacity>
            </View>
          </View>

          {/* Bottone login */}
          <TouchableOpacity
            style={[styles.loginButton, caricamento && styles.loginButtonDisabled]}
            onPress={handleLogin}
            disabled={caricamento}
            activeOpacity={0.8}
          >
            {caricamento ? (
              <ActivityIndicator color={Colors.background} />
            ) : (
              <Text style={styles.loginButtonText}>Accedi</Text>
            )}
          </TouchableOpacity>
        </View>

        {/* Link alla registrazione */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>Non hai un account?</Text>
          <TouchableOpacity onPress={() => router.push('/auth/register')} disabled={caricamento}>
            <Text style={styles.linkText}> Registrati</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: Spacing.lg,
  },
  header: {
    alignItems: 'center',
    marginBottom: Spacing.xxl,
  },
  logoContainer: {
    width: 88,
    height: 88,
    borderRadius: BorderRadius.xl,
    backgroundColor: Colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  title: {
    ...Typography.h1,
    color: Colors.text,
    marginBottom: Spacing.xs,
  },
  subtitle: {
    ...Typography.body,
    color: Colors.textSecondary,
  },
  form: {
    gap: Spacing.md,
  },
  errorBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    backgroundColor: Colors.surface,
    borderWidth: 1,
    borderColor: Colors.error,
    borderRadius: BorderRadius.sm,
    padding: Spacing.md,
  },
  errorText: {
    ...Typography.caption,
    color: Colors.error,
    flex: 1,
  },
  inputWrapper: {
    gap: Spacing.xs,
  },
  label: {
    ...Typography.caption,
    color: Colors.textSecondary,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.surface,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: BorderRadius.sm,
    paddingHorizontal: Spacing.md,
  },
  inputIcon: {
    marginRight: Spacing.sm,
  },
  input: {
    flex: 1,
    height: 48,
    ...Typography.body,
    color: Colors.text,
  },
  eyeButton: {
    padding: Spacing.xs,
  },
  loginButton: {
    backgroundColor: Colors.primary,
    borderRadius: BorderRadius.sm,
    height: 52,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: Spacing.sm,
  },
  loginButtonDisabled: {
    opacity: 0.6,
  },
  loginButtonText: {
    ...Typography.body,
    fontWeight: '700',
    color: Colors.background,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: Spacing.xl,
  },
  footerText: {
    ...Typography.body,
    color: Colors.textSecondary,
  },
  linkText: {
    ...Typography.body,
    color: Colors.primary,
    fontWeight: '600',
  },
});
