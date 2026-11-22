# Demo wykazu AED w lokalnym portalu

Pliki w `dane/` to wykazy AED czterech instytucji z otwartych zbiorów (Legionowo,
Krosno, Przemyśl: CC0 1.0; Warszawa: CC BY 4.0, Otwarte dane Warszawy) przepisane
na wzorcowy zakres danych o AED, oraz wykaz testowy z celowymi błędami
(nie jest to prawdziwa instytucja).

1. `cp env.sample .env`, uzupełnij `AED_DEMO_ADMIN_PASSWORD` i ustawienia z `docker-compose.aed.yml`.
2. Budowa i start (porty tylko na 127.0.0.1):
   `docker compose -f docker-compose.local.yml -f docker-compose.aed.yml up -d mcod-local-admin mcod-local-api mcod-local-celery`
3. Migracje: `docker exec mcod-admin python manage.py migrate`
4. Dane demo: `docker exec -i mcod-admin python manage.py shell < demo_aed/setup_demo.py`
5. Raport zbiorczy od razu: `docker exec mcod-admin python manage.py create_main_aed`
6. Panel administracyjny: http://127.0.0.1:8001/

## Serwer testowy dla jury (tylko wdrożenie, bez zmian w kodzie frontendu)

- Frontend portalu jest zbudowany bez zmian i serwowany przez Caddy z `/srv/frontend` (`Caddyfile`).
- Okno z informacją RODO, które portal pokazuje przy pierwszym wejściu, jest na serwerze testowym wyłączone,
  żeby nie zasłaniało przeglądania: na początku `<head>` w `/srv/frontend/index.html` jest
  `<script>try{localStorage.setItem("OD_isAcquintedWithRodo",JSON.stringify("true"))}catch(e){}</script>`
  (ten sam klucz zapisuje portal po zamknięciu okna; oryginał: `/srv/frontend/index.html.oryginal`).
- Logowanie jury jednym kliknięciem: kod w `data/aed/demo_login_token.txt` na serwerze (poza gitem), zob. `DLA_JURY.md`.
