import pytest

from app.voice import _browser_to_llm, _llm_to_browser


class FakeBrowser:
    def __init__(self, events=None):
        self.events = iter(events or [])
        self.sent_text: list[str] = []
        self.sent_bytes: list[bytes] = []

    async def receive(self):
        return next(self.events)

    async def send_text(self, message: str):
        self.sent_text.append(message)

    async def send_bytes(self, message: bytes):
        self.sent_bytes.append(message)


class FakeUpstream:
    def __init__(self, incoming=None):
        self.sent: list[str | bytes] = []
        self.incoming = list(incoming or [])

    async def send(self, message):
        self.sent.append(message)

    def __aiter__(self):
        self._iterator = iter(self.incoming)
        return self

    async def __anext__(self):
        try:
            return next(self._iterator)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


@pytest.mark.asyncio
async def test_browser_pcm_and_controls_are_forwarded_unchanged() -> None:
    browser = FakeBrowser(
        [
            {"type": "websocket.receive", "text": '{"type":"session.start"}'},
            {"type": "websocket.receive", "bytes": b"pcm16"},
            {"type": "websocket.disconnect"},
        ]
    )
    upstream = FakeUpstream()

    await _browser_to_llm(browser, upstream)

    assert upstream.sent == ['{"type":"session.start"}', b"pcm16"]


@pytest.mark.asyncio
async def test_transcript_delta_and_final_are_forwarded_to_browser() -> None:
    browser = FakeBrowser()
    upstream = FakeUpstream(
        [
            '{"type":"transcript.delta","delta":"Xin"}',
            '{"type":"transcript.final","transcript":"Xin chào"}',
        ]
    )

    await _llm_to_browser(browser, upstream)

    assert browser.sent_text[0].startswith('{"type":"transcript.delta"')
    assert browser.sent_text[1].startswith('{"type":"transcript.final"')
