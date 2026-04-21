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
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Spacing, Typography, BorderRadius } from '../../constants/theme';
import { useAuth } from '../../contexts/AuthContext';

export default function RegisterScreen() {
  const router = useRouter();
  const { register } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confermaPassword, setConfermaPassword] = useState('');
  const [mostraPassword, setMostraPassword] = useState(false);
  const [caricamento, setCaricamento] = useState(false);
  const [errore, setErrore] = useState('');

  // Validazione e invio del form di registrazione
  const handleRegister = async () => {
    if (!email.trim() || !password.trim() || !confermaPassword.trim()) {
      setErrore('Compila tutti i campi.');
      return;
    }
    if (password.trim() !== confermaPassword.trim()) {
      setErrore('Le password non coincidono.');
      return;
    }
    if (password.trim().length < 6) {
      setErrore('La password deve avere almeno 6 caratteri.');
      return;
    }
    try {
      setErrore('');
      setCaricamento(true);
      await register(email.trim(), password.trim());
      // La navigazione avviene automaticamente tramite _layout.tsx (token presente)
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        'Errore durante la registrazione. Riprova.';
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
          <Text style={styles.subtitle}>Crea il tuo account gratuito</Text>
        </View>

        {/* Form di registrazione */}
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
                placeholder="Minimo 6 caratteri"
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

          {/* Conferma password */}
          <View style={styles.inputWrapper}>
            <Text style={styles.label}>Conferma Password</Text>
            <View style={styles.inputContainer}>
              <Ionicons name="lock-closed-outline" size={20} color={Colors.textMuted} style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="Ripeti la password"
                placeholderTextColor={Colors.textMuted}
                value={confermaPassword}
                onChangeText={setConfermaPassword}
                secureTextEntry={!mostraPassword}
                autoCapitalize="none"
              />
            </View>
          </View>

          {/* Bottone registrati */}
          <TouchableOpacity
            style={[styles.registerButton, caricamento && styles.registerButtonDisabled]}
            onPress={handleRegister}
            disabled={caricamento}
            activeOpacity={0.8}
          >
            {caricamento ? (
              <ActivityIndicator color={Colors.background} />
            ) : (
              <Text style={styles.registerButtonText}>Crea Account</Text>
            )}
          </TouchableOpacity>
        </View>

        {/* Link al login */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>Hai già un account?</Text>
          <TouchableOpacity onPress={() => router.back()} disabled={caricamento}>
            <Text style={styles.linkText}> Accedi</Text>
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
    marginBottom: Spacing.xl,
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
  registerButton: {
    backgroundColor: Colors.primary,
    borderRadius: BorderRadius.sm,
    height: 52,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: Spacing.sm,
  },
  registerButtonDisabled: {
    opacity: 0.6,
  },
  registerButtonText: {
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
