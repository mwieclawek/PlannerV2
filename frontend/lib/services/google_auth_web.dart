import 'package:google_sign_in_web/web_only.dart' as web_only;

Future<String?> requestServerAuthCodeOnWeb() async {
  return web_only.requestServerAuthCode();
}
