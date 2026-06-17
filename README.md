# Mercadona Compra

Skill para Codex orientada a crear listas de compra locales y ayudar a prepararlas en Mercadona online.

## Instalacion

### Codex App

En Codex App, abre una conversacion nueva y pega:

```text
Use $skill-installer to install https://github.com/f3rnandomorenoia/skill-codex-mercadona-lecagy-shopping/tree/main/skills/mercadona-compra
```

Reinicia Codex despues de la instalacion para que la skill aparezca como `$mercadona-compra`.

### Manual

```bash
git clone https://github.com/f3rnandomorenoia/skill-codex-mercadona-lecagy-shopping.git
cd skill-codex-mercadona-lecagy-shopping
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/mercadona-compra "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Luego abre una conversacion nueva y usa:

```text
Use $mercadona-compra para crear una lista de compra de Mercadona.
```

## Catalogo local

La skill puede generar un CSV de referencia desde el API publico de la tienda online de Mercadona. Si el CSV no existe, el comando `search` lo descarga automaticamente antes de buscar:

```bash
python3 skills/mercadona-compra/scripts/catalogo_productos.py download
python3 skills/mercadona-compra/scripts/catalogo_productos.py search "leche entera"
```

El catalogo es una ayuda para encontrar productos y SKUs, no una garantia de disponibilidad por direccion, sesion o fecha.

## Seguridad

La skill esta disenada para navegacion asistida. El usuario debe introducir credenciales, direccion, pago y confirmacion final directamente en el navegador. No debe almacenar contrasenas, cookies, tarjetas ni datos de pago.
