/// <reference types="@directus/extensions/api.d.ts" />
import { request } from 'directus:api';

/**
 * Proxies one question to the Asyntai chat API.
 *
 * The Data Studio cannot call another server itself, so the panel posts here
 * and this endpoint makes the outbound call. The sandbox allows it because
 * package.json requests the https://asyntai.com/* scope.
 *
 * The API key is not stored here. The sandbox has no database access, so the
 * panel keeps the key and sends it with each question.
 */
/**
 * Turns a failed request into wording an admin can act on.
 *
 * The sandbox strips everything from the error except its message, so the
 * response body from Asyntai is unreachable. The status code inside that
 * message is the only signal there is.
 */
function explain(error) {
    const text = String(error && error.message ? error.message : error);
    const match = text.match(/status code (\d{3})/);
    const status = match ? Number(match[1]) : 0;

    if (status === 401) {
        return 'Asyntai rejected the API key. Check the key in the panel settings.';
    }

    if (status === 403) {
        return 'Asyntai refused the request. The monthly message limit may be reached, '
            + 'or the plan may not include API access.';
    }

    if (status === 429) {
        return 'Too many requests to Asyntai. Wait a moment and ask again.';
    }

    if (status >= 500) {
        return 'Asyntai is not answering at the moment. Try again shortly.';
    }

    return 'Could not reach Asyntai: ' + text;
}

export default (router) => {
    router.post('/ask', async (req) => {
        const body = req.body || {};

        // Custom endpoints are public. The panel always runs inside a signed in
        // Data Studio, so a missing token means the call did not come from it.
        const headers = req.headers || {};
        const auth = headers.authorization || headers.Authorization || '';
        const cookie = headers.cookie || headers.Cookie || '';

        if (!auth && !cookie) {
            return { status: 401, body: { error: 'Sign in to Directus first.' } };
        }
        const apiKey = String(body.api_key || '').trim();
        const message = String(body.message || '').trim();
        const sessionId = String(body.session_id || '').trim();
        const websiteId = parseInt(String(body.website_id || ''), 10);
        const baseUrl = String(body.base_url || '').trim() || 'https://asyntai.com';

        if (!apiKey) {
            return { status: 400, body: { error: 'Add your Asyntai API key in the panel settings.' } };
        }

        if (!message) {
            return { status: 400, body: { error: 'Type a question first.' } };
        }

        const payload = { message, session_id: sessionId };

        if (Number.isFinite(websiteId) && websiteId > 0) {
            payload.website_id = websiteId;
        }

        let response;

        try {
            response = await request(baseUrl.replace(/\/+$/, '') + '/api/v1/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + apiKey,
                    'User-Agent': 'Asyntai-Directus/1.0',
                },
                body: payload,
            });
        } catch (error) {
            const message = explain(error);
            const scoped = message.indexOf('No permission to request') !== -1;
            return { status: scoped ? 502 : 400, body: { error: message } };
        }

        const data = response && response.data;

        if (!data) {
            return {
                status: 502,
                body: { error: 'Unexpected reply from Asyntai (HTTP ' + (response && response.status) + ').' },
            };
        }

        if (data.success !== true || !data.response) {
            return {
                status: 400,
                body: { error: data.error || 'Asyntai returned no answer.' },
            };
        }

        return {
            status: 200,
            body: { answer: data.response, session_id: data.session_id || sessionId },
        };
    });
};
