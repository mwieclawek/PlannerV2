import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

/// Central error handler and validator for API requests and forms.
class ApiErrorHandler {
  ApiErrorHandler._();

  /// Validates password strength according to system rules:
  /// - Min. 8 characters
  /// - At least one uppercase letter
  /// - At least one digit
  static String? validatePassword(String? value) {
    if (value == null || value.isEmpty) {
      return 'Hasło jest wymagane';
    }
    if (value.length < 8) {
      return 'Hasło musi mieć co najmniej 8 znaków';
    }
    if (!value.contains(RegExp(r'[A-Z]'))) {
      return 'Hasło musi zawierać co najmniej jedną wielką literę';
    }
    if (!value.contains(RegExp(r'[0-9]'))) {
      return 'Hasło musi zawierać co najmniej jedną cyfrę';
    }
    return null;
  }

  /// Extracts a human-friendly Polish error message from any error,
  /// especially [DioException] and FastAPI validation responses.
  static String extractMessage(dynamic error) {
    if (error == null) return 'Wystąpił nieznany błąd';

    if (error is FriendlyDioException) {
      return error.friendlyMessage;
    }

    if (error is DioException) {
      return _extractFromDioException(error);
    }

    // Generic Dart Exception / Error / String
    String raw = error.toString().trim();
    if (raw.startsWith('Exception: ')) {
      raw = raw.substring(11).trim();
    }
    if (raw.startsWith('Błąd: ')) {
      raw = raw.substring(6).trim();
    }
    return translateMessage(raw);
  }

  static String _extractFromDioException(DioException error) {
    final response = error.response;

    if (response != null && response.data != null) {
      final data = response.data;

      // Case 1: JSON Object response
      if (data is Map) {
        // FastAPI standard 'detail' field
        final detail = data['detail'];
        if (detail != null) {
          final parsed = _parseDetail(detail);
          if (parsed.isNotEmpty) return parsed;
        }

        // Alternative message fields
        if (data['message'] != null && data['message'].toString().trim().isNotEmpty) {
          return translateMessage(data['message'].toString());
        }
        if (data['error'] != null && data['error'].toString().trim().isNotEmpty) {
          return translateMessage(data['error'].toString());
        }
        if (data['msg'] != null && data['msg'].toString().trim().isNotEmpty) {
          return translateMessage(data['msg'].toString());
        }
      }

      // Case 2: String response (e.g. text/plain or HTML)
      if (data is String) {
        final text = data.trim();
        // If response is HTML (e.g. Nginx 502/504 Bad Gateway page), ignore HTML tags
        if (text.startsWith('<') || text.toLowerCase().contains('<!doctype html>')) {
          return _statusMessage(response.statusCode);
        }
        if (text.isNotEmpty) {
          return translateMessage(text);
        }
      }
    }

    // If response status code is available but no body message extracted
    if (response != null && response.statusCode != null) {
      return _statusMessage(response.statusCode);
    }

    // Network / Transport errors (no response from server)
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
        return 'Przekroczono limit czasu połączenia z serwerem';
      case DioExceptionType.sendTimeout:
        return 'Przekroczono limit czasu wysyłania danych';
      case DioExceptionType.receiveTimeout:
        return 'Przekroczono limit czasu odpowiedzi serwera';
      case DioExceptionType.badCertificate:
        return 'Błąd certyfikatu bezpieczeństwa połączenia';
      case DioExceptionType.cancel:
        return 'Żądanie zostało anulowane';
      case DioExceptionType.connectionError:
        return 'Brak połączenia z serwerem. Sprawdź połączenie internetowe';
      case DioExceptionType.unknown:
        final inner = error.error;
        if (inner is SocketException ||
            inner.toString().toLowerCase().contains('socket') ||
            inner.toString().toLowerCase().contains('connection refused') ||
            inner.toString().toLowerCase().contains('network is unreachable') ||
            inner.toString().toLowerCase().contains('failed host lookup')) {
          return 'Brak połączenia z serwerem. Sprawdź połączenie internetowe';
        }
        return 'Wystąpił nieoczekiwany błąd sieciowy';
      default:
        return 'Wystąpił błąd podczas komunikacji z serwerem';
    }
  }

  static String _parseDetail(dynamic detail) {
    // 1. detail is a simple String
    if (detail is String) {
      return translateMessage(detail);
    }

    // 2. detail is a List (FastAPI / Pydantic validation errors: [{"loc": [...], "msg": "..."}])
    if (detail is List) {
      final messages = <String>[];
      for (final item in detail) {
        if (item is Map) {
          final msg = item['msg'] ?? item['message'];
          if (msg != null) {
            messages.add(translateMessage(msg.toString()));
          }
        } else if (item != null) {
          messages.add(translateMessage(item.toString()));
        }
      }
      final unique = messages.where((m) => m.isNotEmpty).toSet().toList();
      if (unique.isNotEmpty) {
        return unique.join('\n');
      }
    }

    // 3. detail is a Map (nested field errors)
    if (detail is Map) {
      final messages = <String>[];
      for (final entry in detail.entries) {
        final val = entry.value;
        if (val is String) {
          messages.add(translateMessage(val));
        } else if (val is List) {
          for (final sub in val) {
            messages.add(translateMessage(sub.toString()));
          }
        }
      }
      final unique = messages.where((m) => m.isNotEmpty).toSet().toList();
      if (unique.isNotEmpty) {
        return unique.join('\n');
      }
    }

    return '';
  }

  static String _statusMessage(int? statusCode) {
    switch (statusCode) {
      case 400:
        return 'Nieprawidłowe dane żądania';
      case 401:
        return 'Brak autoryzacji lub sesja wygasła';
      case 403:
        return 'Brak uprawnień do wykonania tej operacji';
      case 404:
        return 'Nie znaleziono żądanego zasobu';
      case 409:
        return 'Wykryto konflikt danych (np. nakładające się terminy)';
      case 422:
        return 'Nieprawidłowe dane formularza';
      case 429:
        return 'Zbyt wiele zapytań. Odczekaj chwilę i spróbuj ponownie';
      case 500:
        return 'Wewnętrzny błąd serwera. Spróbuj ponownie później';
      case 502:
        return 'Błąd bramy serwera (502) - serwer jest niedostępny';
      case 503:
        return 'Serwer jest tymczasowo niedostępny';
      case 504:
        return 'Przekroczono limit czasu odpowiedzi serwera';
      default:
        return 'Wystąpił błąd serwera${statusCode != null ? ' ($statusCode)' : ''}';
    }
  }

  /// Translates known backend error messages (FastAPI/Pydantic/custom) into user-friendly Polish.
  static String translateMessage(String msg) {
    String clean = msg
        .replaceFirst(RegExp(r'^Value error,\s*', caseSensitive: false), '')
        .replaceFirst(RegExp(r'^Assertion failed,\s*', caseSensitive: false), '')
        .trim();

    final lower = clean.toLowerCase();

    // Password errors
    if (lower.contains('incorrect old password')) {
      return 'Stare hasło jest nieprawidłowe';
    }
    if (lower.contains('password must be at least 8 characters')) {
      return 'Hasło musi mieć co najmniej 8 znaków';
    }
    if (lower.contains('password must contain at least one uppercase letter')) {
      return 'Hasło musi zawierać co najmniej jedną wielką literę';
    }
    if (lower.contains('password must contain at least one digit')) {
      return 'Hasło musi zawierać co najmniej jedną cyfrę';
    }

    // Auth / Login errors
    if (lower.contains('incorrect username or password')) {
      return 'Nieprawidłowy login lub hasło';
    }
    if (lower.contains('username exists in multiple restaurants')) {
      return 'Użytkownik istnieje w wielu restauracjach. Podaj kod restauracji lub zaloguj się adresem e-mail.';
    }
    if (lower.contains('deactivated')) {
      return 'Konto jest dezaktywowane. Skontaktuj się z administratorem.';
    }

    // User management errors
    if (lower.contains('restaurant not found')) {
      return 'Restauracja nie została znaleziona';
    }
    if (lower.contains('user not found')) {
      return 'Użytkownik nie został znaleziony';
    }
    if (lower.contains('username already registered') || lower.contains('user already exists')) {
      return 'Użytkownik o takiej nazwie już istnieje';
    }
    if (lower.contains('email already registered')) {
      return 'Ten adres e-mail jest już zarejestrowany';
    }
    if (lower.contains('username must be at least 3 characters')) {
      return 'Nazwa użytkownika musi mieć co najmniej 3 znaki';
    }
    if (lower.contains('username cannot contain spaces')) {
      return 'Nazwa użytkownika nie może zawierać spacji';
    }
    if (lower.contains('invalid email address') || lower.contains('value is not a valid email address')) {
      return 'Nieprawidłowy adres e-mail';
    }
    if (lower.contains('cannot deactivate yourself')) {
      return 'Nie możesz dezaktywować własnego konta';
    }
    if (lower.contains('cannot delete yourself')) {
      return 'Nie możesz usunąć własnego konta';
    }

    // Shift / Schedule errors
    if (lower.contains('shift overlap detected')) {
      return 'Wykryto nakładanie się zmian';
    }
    if (lower.contains('shift already assigned')) {
      return 'Ta zmiana jest już przypisana';
    }
    if (lower.contains('insufficient rest time')) {
      return 'Zbyt krótki odpoczynek między zmianami (wymagane min. 11h)';
    }

    // Generic validation errors
    if (lower == 'field required') {
      return 'To pole jest wymagane';
    }
    if (lower.contains('string should have at least')) {
      return 'Wprowadzony tekst jest za krótki';
    }

    return clean;
  }

  /// Convenience helper to show a consistent error SnackBar.
  static void showErrorSnackBar(BuildContext context, dynamic error, {String prefix = ''}) {
    final message = extractMessage(error);
    final text = prefix.isNotEmpty ? '$prefix$message' : message;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(text),
        backgroundColor: Theme.of(context).colorScheme.error,
      ),
    );
  }
}

/// A specialized [DioException] that displays a clean, user-friendly
/// Polish message when printed with `toString()` (such as in `Text('Błąd: $e')`).
class FriendlyDioException extends DioException {
  final String friendlyMessage;

  FriendlyDioException({
    required super.requestOptions,
    super.response,
    super.type,
    super.error,
    super.stackTrace,
    super.message,
    required this.friendlyMessage,
  });

  factory FriendlyDioException.fromDioException(DioException e) {
    final friendly = ApiErrorHandler.extractMessage(e);
    return FriendlyDioException(
      requestOptions: e.requestOptions,
      response: e.response,
      type: e.type,
      error: e.error,
      stackTrace: e.stackTrace,
      message: friendly,
      friendlyMessage: friendly,
    );
  }

  @override
  String toString() => friendlyMessage;
}
