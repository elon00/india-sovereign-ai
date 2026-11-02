"""Opt-in Gemini text planning. Model output never executes tools or transactions."""
import json
import re
from urllib.request import Request, build_opener, HTTPRedirectHandler


class IntegrationError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


class GeminiPlanner:
    def __init__(self, *, api_key, models, enabled=False, max_requests=1, timeout=10):
        if (not isinstance(api_key, str) or not api_key.strip()
                or not isinstance(models, (list, tuple)) or not models
                or any(not isinstance(m, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}', m) for m in models)
                or type(max_requests) is not int or not 1 <= max_requests <= 10
                or type(timeout) not in (int, float) or not 0 < timeout <= 30
                or type(enabled) is not bool):
            raise ValueError('Explicit key, allowed model IDs and bounded request settings required')
        self._key, self._models = api_key, tuple(models)
        self._enabled, self._remaining, self._timeout = enabled, max_requests, timeout

    def plan(self, prompt, *, model):
        if not self._enabled or self._remaining <= 0:
            raise IntegrationError('AI_DISABLED_OR_REQUEST_BUDGET_EXHAUSTED')
        if model not in self._models:
            raise ValueError('Model is not in the configured allowlist')
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 8000:
            raise ValueError('Prompt must contain 1 to 8000 characters')
        body = {'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
                'systemInstruction': {'parts': [{'text': 'Return advisory text only. You have no tools, wallet, execution authority or access to secrets. Never claim transactions or deployments occurred.'}]},
                'generationConfig': {'maxOutputTokens': 1024}}
        request = Request('https://generativelanguage.googleapis.com/v1beta/models/' + model + ':generateContent',
                          data=json.dumps(body).encode(), method='POST',
                          headers={'Content-Type': 'application/json', 'x-goog-api-key': self._key})
        # Consume failed attempts too. This is a process-local request cap, not a billing cap.
        self._remaining -= 1
        try:
            with build_opener(NoRedirect()).open(request, timeout=self._timeout) as response:
                data = response.read(65537)
            if len(data) > 65536:
                raise ValueError('Response too large')
            packet = json.loads(data)
            candidate = packet['candidates'][0]
            if candidate.get('finishReason') != 'STOP':
                raise ValueError('Incomplete or blocked response')
            parts = candidate['content']['parts']
            if not isinstance(parts, list) or not parts or any(set(p) != {'text'} or not isinstance(p['text'], str) for p in parts):
                raise ValueError('Only text responses are accepted')
            text = ''.join(p['text'] for p in parts)
            if not text.strip() or len(text) > 16000:
                raise ValueError('Invalid response length')
            return {'status': 'ADVISORY_TEXT_ONLY', 'model': model, 'text': text,
                    'toolsExecuted': False, 'transactionSubmitted': False}
        except Exception:
            # Exceptions can contain credential-bearing URLs, headers or response bodies.
            raise IntegrationError('AI_RESPONSE_UNAVAILABLE_OR_INVALID') from None
