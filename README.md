# Asyntai for Directus

Ask your Asyntai assistant questions from inside the Directus Data Studio.
Answers come from your own content: your website, your uploaded documents and
your help centre articles.

## Two packages, and why

Directus refuses to let an app extension call another server, and its
marketplace only lists API extensions that run in the sandbox. A bundle cannot
hold a sandboxed endpoint, because `registerBundleExtension` imports the
bundle's API file directly and never looks at the `sandbox` setting. So this
ships as two extensions:

| Folder        | Package                              | What it is                          |
|---------------|--------------------------------------|-------------------------------------|
| `asyntai/`    | `directus-extension-asyntai`         | The panel in the Data Studio        |
| `asyntai-api/`| `directus-extension-asyntai-api`     | Sandboxed endpoint that calls Asyntai |

Both are needed. The panel posts to the endpoint, and the endpoint makes the
one outbound request, which the sandbox permits because the manifest asks for
the `https://asyntai.com/*` scope.

The API key is kept by the panel, not the endpoint. The sandbox has no database
access, so there is nowhere on the server to store it.

## Build

    cd asyntai     && npm install && npm run build
    cd asyntai-api && npm install && npm run build

## Test

Directus 11 in Docker, with a stub standing in for the Asyntai API:

    python tests/test_extension.py

The stub lives in `../rocketchat/tests/stub_api.py` style; see the session notes.
To exercise a local stub you must widen the sandbox scope in the *installed copy*
of `asyntai-api/package.json`. Never widen it in the shipped package.

## Publish

The Directus Marketplace mirrors npm. There is no submission form:

    cd asyntai     && npm publish
    cd asyntai-api && npm publish

The registry picks up anything carrying the `directus-extension` keyword within
a few hours.
