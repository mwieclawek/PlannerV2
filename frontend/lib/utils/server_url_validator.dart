import 'package:flutter/foundation.dart';

/// Validation of the backend server URL entered manually or scanned from a QR code.
///
/// A malicious QR code could point the app at an attacker-controlled server (phishing:
/// credentials would be sent to it). Therefore only well-formed `http(s)` URLs with a host
/// are accepted, and in release builds only `https://` is allowed.
class ServerUrlValidator {
  ServerUrlValidator._();

  /// Returns the normalized URL (no trailing slash) or `null` when invalid.
  /// [releaseMode] defaults to [kReleaseMode]; it is injectable for tests.
  static String? normalize(String? raw, {bool? releaseMode}) {
    final isRelease = releaseMode ?? kReleaseMode;
    if (raw == null) return null;
    final value = raw.trim();
    if (value.isEmpty) return null;

    final uri = Uri.tryParse(value);
    if (uri == null || !uri.hasScheme || !uri.hasAuthority || uri.host.isEmpty) {
      return null;
    }

    final scheme = uri.scheme.toLowerCase();
    if (scheme != 'https' && scheme != 'http') return null; // javascript:, file:, intent: ...
    if (isRelease && scheme != 'https') return null; // plain http only allowed in debug
    if (uri.userInfo.isNotEmpty) return null; // https://trusted.com@evil.com style tricks

    return value.endsWith('/') ? value.substring(0, value.length - 1) : value;
  }

  /// Human readable validation error, or `null` if the URL is acceptable.
  static String? errorFor(String? raw, {bool? releaseMode}) {
    final isRelease = releaseMode ?? kReleaseMode;
    if (normalize(raw, releaseMode: releaseMode) != null) return null;
    final uri = Uri.tryParse((raw ?? '').trim());
    if (isRelease && uri != null && uri.scheme.toLowerCase() == 'http') {
      return 'Adres serwera musi używać protokołu https://';
    }
    return 'Nieprawidłowy adres serwera';
  }
}
