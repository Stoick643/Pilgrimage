# How Couch Traveller Actually Works
*The "explain it at a bar" version*

---

## The Magic Trick

You type "Sicily, 5 days" and text starts appearing word by word, like someone is typing it for you. Photos pop in. Weather appears. A map draws itself. Then you can share the whole thing with a link.

Behind the scenes, this is five things pretending to be one smooth experience.

---

## 1. The Typewriter (Streaming)

Remember those old movies where a telegram arrives and the machine types it out letter by letter? That's what we're doing, except the "telegraph operator" is an AI in a data center somewhere.

The AI doesn't write the whole itinerary and then send it. It **thinks out loud** — word by word, line by line. Each fragment flies from the AI to our server to your browser in real time.

Here's the catch: the AI doesn't send neat sentences. It sends random chunks like `"&&& Pal"` and then `"ermo\nDay 1"`. Imagine receiving a telegram where the operator sometimes hits "send" mid-word.

So we have a **waiting room** (we call it `lineBuffer`). Chunks arrive and sit in the waiting room until we see a line break. Only then do we process a complete line. It's like assembling a jigsaw puzzle where pieces arrive by mail — you wait until you have enough to see the picture.

That's literally the hardest part of the whole app. Everything else is plumbing.

---

## 2. The Filing Cabinet (Caching)

LLM calls are slow (10-20 seconds) and cost real money per request. So after the AI writes a Sicily 5-day itinerary, we **save a copy** in a little SQLite database.

Next time someone asks for the exact same thing — same country, same days, same activities, same language — we just replay the saved copy. Instant. Free.

It's like a waiter who memorizes your order. "Ah, Sicily 5 days with food and history? I made that one this morning — here you go!"

The copy expires after 24 hours. Because yesterday's "perfect plan" should occasionally get a fresh take.

---

## 3. The Photo Wall (City Images)

When the AI mentions a new city, we immediately ask Unsplash: "Hey, got a nice photo of Palermo?"

But here's a problem we didn't see coming: what if the AI plans **two days in Rome**? You'd see the Colosseum twice. Boring.

The fix is embarrassingly simple. We count. First time Rome appears: ask Unsplash for page 1 of results. Second time: page 2. Different page, different photo. The Colosseum, then the Trevi Fountain. Same city, different vibe.

Each day card remembers which "page" it got (`data-page="1"` or `data-page="2"`), so the right photo goes to the right card. Like name tags at a party.

---

## 4. The Mixtape (Sharing)

Here's something sneaky: while you're watching the text stream in, a silent string variable called `fullStreamText` is secretly recording everything. Every chunk the AI sends gets appended to it. The variable just sits there, growing, saying nothing.

When you click "Share", that hidden recording gets sent to our server, which gives it a random 12-character name (like `8fe47bcf43e8`) and stuffs it in the database.

Now `pilgrimage.fly.dev/trip/8fe47bcf43e8` is a permanent link. When someone opens it, we pull the saved text from the database and replay it — not streaming this time, just rendering it all at once. Same photos load, same weather, same maps. No AI involved.

It's like recording a live concert and selling the album. The performance happened once; the recording plays forever.

---

## 5. The Secret Handshake (`&&&`)

How does the browser know when the AI starts talking about a new city? We needed a signal — something the AI would write that we could detect instantly mid-stream.

We chose `&&&`. Three ampersands on a line by itself, followed by the city name:

```
&&& Palermo
Day 1: Explore the old town...

&&& Catania
Day 2: Mount Etna...
```

Why `&&&`? Because no travel writer would ever naturally write that. It's ugly and meaningless — which makes it a perfect machine signal. Like a dog whistle: the browser hears it, humans don't see it.

The previous version (V2) tried using JSON — structured data with curly braces. That was a nightmare. When text streams character by character, you need to count opening and closing braces to know when a JSON object is complete. Miss one brace and everything breaks. `&&&` is brain-dead simple: `if (line.startsWith('&&&'))` — done.

Sometimes the dumb solution is the smart solution.

---

## The Whole Thing in One Breath

You type Sicily. The browser asks the server. The server asks the AI. The AI starts rambling word by word. Each word flies to your browser through a pipe called SSE. A little buffer stitches word-fragments into complete lines. When a line says `&&&`, we know a new city started — create a card, fetch a photo, fetch the weather. When the AI stops talking, we save the whole thing to cache (for speed) and show you a map. If you click Share, the secret recording gets saved to the database with a random name, and you get a link you can send to anyone.

Nine thousand lines of code. But that paragraph is the whole story.

---

*Technical details: see [architecture.md](architecture.md)*
