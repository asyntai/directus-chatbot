<script setup>
import { computed, nextTick, onMounted, ref } from 'vue';
import { useApi } from '@directus/extensions-sdk';

const api = useApi();

// The sandbox cannot reach the database, so the key lives here in the browser
// and travels with each question.
const STORE_KEY = 'asyntai:settings';

const apiKey = ref('');
const websiteId = ref('');
const showSettings = ref(false);
const saved = ref(false);

const question = ref('');
const messages = ref([]);
const busy = ref(false);
const errorText = ref('');
const thread = ref(null);

const sessionId = ref('directus_' + Math.random().toString(36).slice(2, 12));
const ready = computed(() => apiKey.value.trim() !== '');

function loadSettings() {
    try {
        const raw = window.localStorage.getItem(STORE_KEY);
        if (!raw) return;
        const data = JSON.parse(raw);
        apiKey.value = data.apiKey || '';
        websiteId.value = data.websiteId || '';
    } catch (e) {
        // A corrupt entry is not worth failing over; the panel just starts empty.
    }
}

function saveSettings() {
    window.localStorage.setItem(STORE_KEY, JSON.stringify({
        apiKey: apiKey.value.trim(),
        websiteId: websiteId.value.trim(),
    }));
    saved.value = true;
    errorText.value = '';
    window.setTimeout(() => { saved.value = false; }, 2500);
    if (ready.value) showSettings.value = false;
}

async function scrollDown() {
    await nextTick();
    if (thread.value) thread.value.scrollTop = thread.value.scrollHeight;
}

async function ask() {
    const text = question.value.trim();
    if (!text || busy.value) return;

    if (!ready.value) {
        showSettings.value = true;
        errorText.value = 'Add your Asyntai API key first.';
        return;
    }

    messages.value.push({ role: 'you', text });
    question.value = '';
    errorText.value = '';
    busy.value = true;
    scrollDown();

    try {
        // Directus mounts a standalone endpoint under its extension name.
        const res = await api.post('/directus-extension-asyntai-api/ask', {
            api_key: apiKey.value.trim(),
            message: text,
            session_id: sessionId.value,
            website_id: websiteId.value.trim(),
        });
        messages.value.push({ role: 'asyntai', text: res.data.answer });
    } catch (error) {
        const detail = error?.response?.data?.error || error?.message || 'Unknown error';
        errorText.value = detail;
    } finally {
        busy.value = false;
        scrollDown();
    }
}

function newConversation() {
    messages.value = [];
    errorText.value = '';
    sessionId.value = 'directus_' + Math.random().toString(36).slice(2, 12);
}

onMounted(() => {
    loadSettings();
    if (!ready.value) showSettings.value = true;
});
</script>

<template>
    <private-view title="Asyntai">
        <template #navigation></template>

        <template #actions>
            <v-button v-tooltip.bottom="'New conversation'" rounded icon secondary @click="newConversation">
                <v-icon name="refresh" />
            </v-button>
            <v-button v-tooltip.bottom="'Settings'" rounded icon secondary @click="showSettings = !showSettings">
                <v-icon name="settings" />
            </v-button>
        </template>

        <div class="asyntai-page">
            <div v-if="showSettings" class="asyntai-card">
                <h2>Settings</h2>
                <p class="asyntai-help">
                    Your API key is on the
                    <a href="https://asyntai.com/settings/api/" target="_blank" rel="noopener">API settings</a>
                    page in your Asyntai dashboard. API access needs a paid Asyntai plan.
                </p>

                <label class="asyntai-label" for="asyntai-key">Asyntai API key</label>
                <input id="asyntai-key" v-model="apiKey" class="asyntai-input" type="password"
                    placeholder="Paste your API key" autocomplete="off" />

                <label class="asyntai-label" for="asyntai-site">Website ID (optional)</label>
                <input id="asyntai-site" v-model="websiteId" class="asyntai-input" type="text"
                    placeholder="Leave empty to use your primary website" />

                <div class="asyntai-row">
                    <v-button small @click="saveSettings">Save</v-button>
                    <span v-if="saved" class="asyntai-saved">Saved</span>
                </div>

                <p class="asyntai-note">
                    The same Asyntai account also answers your website visitors. Add the chat widget
                    to your public site with one snippet, and both the widget and this panel answer
                    from the same content.
                    <a href="https://asyntai.com/documentation/installation/" target="_blank" rel="noopener">
                        How to add the widget
                    </a>
                </p>
            </div>

            <div class="asyntai-card asyntai-chat">
                <div ref="thread" class="asyntai-thread">
                    <div v-if="messages.length === 0" class="asyntai-empty">
                        <v-icon name="chat" large />
                        <p>Ask a question and Asyntai answers from your own content:
                            your website, your documents and your help centre articles.</p>
                        <p class="asyntai-examples">
                            For example: what is our refund policy, how do I request time off,
                            which page explains our pricing.
                        </p>
                    </div>

                    <div v-for="(m, i) in messages" :key="i" class="asyntai-msg" :class="'asyntai-' + m.role">
                        <div class="asyntai-who">{{ m.role === 'you' ? 'You' : 'Asyntai' }}</div>
                        <div class="asyntai-text">{{ m.text }}</div>
                    </div>

                    <div v-if="busy" class="asyntai-msg asyntai-asyntai">
                        <div class="asyntai-who">Asyntai</div>
                        <div class="asyntai-text asyntai-thinking">Thinking…</div>
                    </div>
                </div>

                <p v-if="errorText" class="asyntai-error">{{ errorText }}</p>

                <form class="asyntai-form" @submit.prevent="ask">
                    <input v-model="question" class="asyntai-input asyntai-ask" type="text"
                        placeholder="Ask a question…" :disabled="busy" />
                    <v-button :disabled="busy || question.trim() === ''" @click="ask">Ask</v-button>
                </form>
            </div>
        </div>
    </private-view>
</template>

<style scoped>
.asyntai-page {
    padding: 0 32px 32px;
    max-width: 900px;
}

.asyntai-card {
    background: var(--theme--background-normal, var(--background-normal));
    border-radius: var(--theme--border-radius, 6px);
    padding: 20px;
    margin-bottom: 20px;
}

.asyntai-card h2 {
    margin: 0 0 8px;
    font-size: 16px;
    font-weight: 600;
}

.asyntai-help,
.asyntai-note {
    color: var(--theme--foreground-subdued, var(--foreground-subdued));
    font-size: 13px;
    margin: 0 0 16px;
    line-height: 1.5;
}

.asyntai-note {
    margin: 20px 0 0;
    padding-top: 16px;
    border-top: 1px solid var(--theme--border-color-subdued, var(--border-subdued));
}

.asyntai-label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    margin: 12px 0 4px;
}

.asyntai-input {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid var(--theme--form--field--input--border-color, var(--border-normal));
    border-radius: var(--theme--border-radius, 6px);
    background: var(--theme--form--field--input--background, var(--background-page));
    color: var(--theme--foreground, var(--foreground-normal));
    font-family: inherit;
    font-size: 14px;
    box-sizing: border-box;
}

.asyntai-input:focus {
    outline: none;
    border-color: var(--theme--primary, var(--primary));
}

.asyntai-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 16px;
}

.asyntai-saved {
    color: var(--theme--success, var(--success));
    font-size: 13px;
}

.asyntai-chat {
    display: flex;
    flex-direction: column;
}

.asyntai-thread {
    min-height: 280px;
    max-height: 46vh;
    overflow-y: auto;
    margin-bottom: 16px;
}

.asyntai-empty {
    text-align: center;
    color: var(--theme--foreground-subdued, var(--foreground-subdued));
    padding: 48px 24px;
}

.asyntai-empty p {
    margin: 12px auto 0;
    max-width: 420px;
    line-height: 1.5;
}

.asyntai-examples {
    font-size: 13px;
    opacity: 0.8;
}

.asyntai-msg {
    margin-bottom: 16px;
}

.asyntai-who {
    font-size: 12px;
    font-weight: 600;
    color: var(--theme--foreground-subdued, var(--foreground-subdued));
    margin-bottom: 4px;
}

.asyntai-text {
    line-height: 1.6;
    white-space: pre-wrap;
}

.asyntai-asyntai .asyntai-text {
    background: var(--theme--background-subdued, var(--background-subdued));
    padding: 12px 14px;
    border-radius: var(--theme--border-radius, 6px);
}

.asyntai-thinking {
    color: var(--theme--foreground-subdued, var(--foreground-subdued));
}

.asyntai-error {
    color: var(--theme--danger, var(--danger));
    font-size: 13px;
    margin: 0 0 12px;
}

.asyntai-form {
    display: flex;
    gap: 12px;
}

.asyntai-ask {
    flex: 1;
}
</style>
