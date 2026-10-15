import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/utils/api_error_handler.dart';

void main() {
  group('ApiErrorHandler.validatePassword', () {
    test('rejects empty or null password', () {
      expect(ApiErrorHandler.validatePassword(null), 'Hasło jest wymagane');
      expect(ApiErrorHandler.validatePassword(''), 'Hasło jest wymagane');
    });

    test('rejects passwords shorter than 8 characters', () {
      expect(ApiErrorHandler.validatePassword('Pass1'), 'Hasło musi mieć co najmniej 8 znaków');
      expect(ApiErrorHandler.validatePassword('Pass123'), 'Hasło musi mieć co najmniej 8 znaków');
    });

    test('rejects passwords without uppercase letters', () {
      expect(ApiErrorHandler.validatePassword('password123'), 'Hasło musi zawierać co najmniej jedną wielką literę');
    });

    test('rejects passwords without digits', () {
      expect(ApiErrorHandler.validatePassword('PasswordFull'), 'Hasło musi zawierać co najmniej jedną cyfrę');
    });

    test('accepts valid passwords', () {
      expect(ApiErrorHandler.validatePassword('Password123'), isNull);
      expect(ApiErrorHandler.validatePassword('Admin2026!'), isNull);
    });
  });

  group('ApiErrorHandler.extractMessage', () {
    test('extracts detail string from DioException', () {
      final dioException = DioException(
        requestOptions: RequestOptions(path: '/auth/change-password'),
        response: Response(
          requestOptions: RequestOptions(path: '/auth/change-password'),
          statusCode: 400,
          data: {'detail': 'Incorrect old password'},
        ),
      );

      final msg = ApiErrorHandler.extractMessage(dioException);
      expect(msg, 'Stare hasło jest nieprawidłowe');
    });

    test('extracts Pydantic validation error list from 422', () {
      final dioException = DioException(
        requestOptions: RequestOptions(path: '/auth/change-password'),
        response: Response(
          requestOptions: RequestOptions(path: '/auth/change-password'),
          statusCode: 422,
          data: {
            'detail': [
              {
                'loc': ['body', 'new_password'],
                'msg': 'Value error, Password must be at least 8 characters',
                'type': 'value_error',
              }
            ]
          },
        ),
      );

      final msg = ApiErrorHandler.extractMessage(dioException);
      expect(msg, 'Hasło musi mieć co najmniej 8 znaków');
    });

    test('extracts multiple Pydantic validation errors and joins them', () {
      final dioException = DioException(
        requestOptions: RequestOptions(path: '/manager/users'),
        response: Response(
          requestOptions: RequestOptions(path: '/manager/users'),
          statusCode: 422,
          data: {
            'detail': [
              {
                'loc': ['body', 'password'],
                'msg': 'Value error, Password must contain at least one uppercase letter',
              },
              {
                'loc': ['body', 'username'],
                'msg': 'Value error, Username cannot contain spaces',
              }
            ]
          },
        ),
      );

      final msg = ApiErrorHandler.extractMessage(dioException);
      expect(msg, contains('Hasło musi zawierać co najmniej jedną wielką literę'));
      expect(msg, contains('Nazwa użytkownika nie może zawierać spacji'));
    });

    test('extracts message field if detail is absent', () {
      final dioException = DioException(
        requestOptions: RequestOptions(path: '/sysadmin/restaurants'),
        response: Response(
          requestOptions: RequestOptions(path: '/sysadmin/restaurants'),
          statusCode: 400,
          data: {'message': 'Restaurant not found'},
        ),
      );

      final msg = ApiErrorHandler.extractMessage(dioException);
      expect(msg, 'Restauracja nie została znaleziona');
    });

    test('maps status code if response data is empty or HTML', () {
      final htmlDioException = DioException(
        requestOptions: RequestOptions(path: '/'),
        response: Response(
          requestOptions: RequestOptions(path: '/'),
          statusCode: 502,
          data: '<html><body>502 Bad Gateway</body></html>',
        ),
      );

      final msg = ApiErrorHandler.extractMessage(htmlDioException);
      expect(msg, contains('Błąd bramy serwera (502)'));
    });

    test('handles network errors without response', () {
      final timeoutException = DioException(
        requestOptions: RequestOptions(path: '/'),
        type: DioExceptionType.connectionTimeout,
      );
      expect(
        ApiErrorHandler.extractMessage(timeoutException),
        'Przekroczono limit czasu połączenia z serwerem',
      );

      final connError = DioException(
        requestOptions: RequestOptions(path: '/'),
        type: DioExceptionType.connectionError,
      );
      expect(
        ApiErrorHandler.extractMessage(connError),
        'Brak połączenia z serwerem. Sprawdź połączenie internetowe',
      );
    });

    test('FriendlyDioException returns friendlyMessage in toString()', () {
      final dioException = DioException(
        requestOptions: RequestOptions(path: '/auth/change-password'),
        response: Response(
          requestOptions: RequestOptions(path: '/auth/change-password'),
          statusCode: 400,
          data: {'detail': 'Incorrect old password'},
        ),
      );

      final friendly = FriendlyDioException.fromDioException(dioException);
      expect(friendly.toString(), 'Stare hasło jest nieprawidłowe');
      expect('$friendly', 'Stare hasło jest nieprawidłowe');
      expect(friendly, isA<DioException>());
      expect(friendly.response?.statusCode, 400);
    });
  });
}
