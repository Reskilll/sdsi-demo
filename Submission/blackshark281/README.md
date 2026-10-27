# URL Shortener with Analytics

A Spring Boot 3 application that shortens URLs, resolves them with HTTP redirects, and tracks click analytics per link.

## Quick Start

### Prerequisites
- Java 17+
- Maven 3.8+

### Build & Run

```bash
# Compile and run
mvn spring-boot:run

# Or build a jar and run it
mvn clean package -DskipTests
java -jar target/url-shortener-1.0.0.jar
```

The app starts on **http://localhost:8080** with:
- **Frontend UI** at `/` — shorten URLs and view stats
- **H2 Console** at `/h2-console` (JDBC URL: `jdbc:h2:file:./data/urlshortener`, user: `sa`, no password)

### Tests

```bash
mvn test
```

Includes:
- **Unit tests** for `Base62Encoder`, `UrlValidator`, `UrlShortenerService`
- **Integration test** (`UrlShortenerIntegrationTest`) covering the full shorten→resolve→stats flow

---

## API Reference

### POST `/api/shorten` — Shorten a URL

**Request body:**

```json
{
  "url": "https://example.com/very-long-url",
  "customAlias": "myLink",          // optional, 4-20 alphanumeric chars
  "expiryDays": 30                  // optional
}
```

**Response (201 Created):**

```json
{
  "shortCode": "00000a",
  "shortUrl": "http://localhost:8080/00000a",
  "originalUrl": "https://example.com/very-long-url",
  "createdAt": "2026-10-27T12:00:00Z",
  "expiresAt": "2026-11-26T12:00:00Z"
}
```

### GET `/{code}` — Resolve a short code

- **302 Found** → redirects to the original URL
- **404 Not Found** → unknown code
- **410 Gone** → link has expired

### GET `/api/stats/{code}` — Get click statistics

```json
{
  "shortCode": "00000a",
  "originalUrl": "https://example.com/very-long-url",
  "totalClicks": 42,
  "lastAccessedAt": "2026-10-27T15:30:00Z",
  "clicksPerDay": {
    "2026-10-26": 15,
    "2026-10-27": 27
  },
  "createdAt": "2026-10-25T12:00:00Z",
  "expiresAt": null,
  "expired": false
}
```

---

## Architecture

```
src/
├── main/java/com/urlshortener/
│   ├── UrlShortenerApplication.java      # Spring Boot entry point
│   ├── config/
│   │   └── WebConfig.java                # CORS configuration
│   ├── controller/
│   │   └── UrlShortenerController.java   # REST endpoints + exception handlers
│   ├── dto/
│   │   ├── ShortenRequest.java           # Request DTO with validation
│   │   ├── ShortenResponse.java          # Shorten response DTO
│   │   └── StatsResponse.java            # Stats response DTO
│   ├── model/
│   │   ├── ShortenedUrl.java             # JPA entity for URL mappings
│   │   └── ClickEvent.java              # JPA entity for individual clicks
│   ├── repository/
│   │   ├── ShortenedUrlRepository.java   # Spring Data JPA repository
│   │   └── ClickEventRepository.java     # Click event queries
│   ├── service/
│   │   └── UrlShortenerService.java      # Core business logic
│   └── util/
│       ├── Base62Encoder.java            # ID ↔ base62 encoding
│       └── UrlValidator.java             # URL validation & scheme filtering
├── resources/
│   ├── application.properties            # App configuration (H2 DB)
│   └── static/
│       └── index.html                    # Frontend UI
└── test/                                 # Unit & integration tests
```

## Design Decisions

| Concern          | Approach |
|------------------|----------|
| **Code generation** | Base62 encode the auto-increment DB primary key. Guarantees uniqueness, no collisions, minimum 6 characters. |
| **Idempotency** | Look up by `originalUrl` before inserting. Same URL without custom alias always returns the same code. |
| **Custom aliases** | Stored directly as the `shortCode`. Collision-checks against both DB and reserved words. |
| **URL validation** | Explicit scheme allowlist (http/https only). Blocks `javascript:`, `data:`, `file:`, `mailto:`, etc. before any parsing. |
| **Expiry** | Optional `expiresAt` field. Resolving an expired link returns 410 Gone. |
| **Analytics** | Each resolution writes a `ClickEvent` row. Aggregated counts live on `ShortenedUrl` for fast reads. Daily breakdown via `GROUP BY DATE(clicked_at)`. |
| **Database** | H2 file-based DB. Zero setup, persists across restarts. Swap to PostgreSQL/MySQL by changing `application.properties`. |
| **Security** | Input validation via Bean Validation + URL scheme filtering. Reserved alias prefixes blocked. Headers truncated before storage. |