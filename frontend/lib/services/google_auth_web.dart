import 'package:google_sign_in/google_sign_in.dart';
import 'package:google_sign_in_web/web_only.dart' as web_only;

Future<String?> requestServerAuthCodeOnWeb([GoogleSignIn? googleSignIn]) async {
  final gsi = googleSignIn ??
      GoogleSignIn(
        scopes: ['https://www.googleapis.com/auth/calendar.events'],
        forceCodeForRefreshToken: true,
      );
  // Ensure the web plugin and GIS SDK are initialized before calling web_only.requestServerAuthCode()
  try {
    await gsi.isSignedIn();
  } catch (_) {}
  return await web_only.requestServerAuthCode();
}
