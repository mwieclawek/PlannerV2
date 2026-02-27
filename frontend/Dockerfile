# Etap 1: Obraz Dart/Flutter
FROM ghcr.io/cirruslabs/flutter:stable AS build

WORKDIR /app
COPY . .

RUN flutter clean
RUN flutter pub get
ARG FLUTTER_ENV=dev
RUN flutter build web --release --dart-define=ENV=${FLUTTER_ENV}

# Etap 2: Serwer Nginx
FROM nginx:alpine

# Tworzymy katalog, z którego nginx.conf serwuje aplikację
RUN mkdir -p /var/www/plannerv2/web

# Skopiowanie wyniku budowania z etapu 1
COPY --from=build /app/build/web /var/www/plannerv2/web
