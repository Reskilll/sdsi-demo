package com.booking;

import java.io.*;
import java.net.*;
import java.net.http.*;
import java.net.http.HttpRequest.BodyPublishers;
import java.net.http.HttpResponse.BodyHandlers;
import java.time.Duration;

/**
 * Standalone test runner — starts the app then runs the test suite via HTTP.
 * Zero test-framework dependencies; just java.net.http.
 */
public class StandaloneTestRunner {

    private static final HttpClient client = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5)).build();
    private static final String BASE = "http://localhost:8080/api/bookings";
    private static int passed, failed;

    public static void main(String[] args) throws Exception {
        System.out.println("\n===== Meeting Room Booking — Test Suite =====\n");

        // M1: CRUD
        test("M1 create booking", () -> {
            var r = post(BASE, json("roomId","r2","organiser","alice",
                    "date","2026-11-01","start","10:00","end","11:00",
                    "attendees","[\"alice\",\"bob\"]"));
            check(r.statusCode() == 201, "status 201");
            check(r.body().contains("\"roomId\":\"r2\""), "contains roomId");
            String id = extractId(r.body());
            check(id != null && !id.isEmpty(), "id assigned: " + id);
        });

        test("M1 read not-found", () -> {
            var r = get(BASE + "/nonexistent");
            check(r.statusCode() == 404, "status 404");
        });

        test("M1 update booking", () -> {
            // create
            var cr = post(BASE, json("roomId","r3","organiser","bob",
                    "date","2026-11-02","start","09:00","end","10:00",
                    "attendees","[\"bob\"]"));
            String id = extractId(cr.body());
            // update
            var ur = put(BASE + "/" + id, json("roomId","r4","organiser","bob",
                    "date","2026-11-02","start","09:30","end","10:30",
                    "attendees","[\"bob\",\"carol\"]"));
            check(ur.statusCode() == 200, "status 200");
            check(ur.body().contains("\"roomId\":\"r4\""), "room changed");
            check(ur.body().contains("\"carol\""), "attendees updated");
        });

        test("M1 delete booking", () -> {
            var cr = post(BASE, json("roomId","r1","organiser","dan",
                    "date","2026-11-03","start","14:00","end","15:00",
                    "attendees","[\"dan\"]"));
            String id = extractId(cr.body());
            var dr = delete(BASE + "/" + id);
            check(dr.statusCode() == 204, "delete status 204");
            var gr = get(BASE + "/" + id);
            check(gr.statusCode() == 404, "gone after delete");
        });

        // M2: Overlap
        test("M2 reject overlap", () -> {
            post(BASE, json("roomId","r2","organiser","eve",
                    "date","2026-11-04","start","10:00","end","12:00",
                    "attendees","[\"eve\"]"));
            var r = post(BASE, json("roomId","r2","organiser","frank",
                    "date","2026-11-04","start","11:00","end","13:00",
                    "attendees","[\"frank\"]"));
            check(r.statusCode() == 409, "status 409 conflict");
        });

        test("M2 allow back-to-back", () -> {
            post(BASE, json("roomId","r3","organiser","grace",
                    "date","2026-11-05","start","10:00","end","11:00",
                    "attendees","[\"grace\"]"));
            var r = post(BASE, json("roomId","r3","organiser","heidi",
                    "date","2026-11-05","start","11:00","end","12:00",
                    "attendees","[\"heidi\"]"));
            check(r.statusCode() == 201, "status 201 — back-to-back OK");
        });

        // M3: Capacity
        test("M3 reject capacity exceeded", () -> {
            var r = post(BASE, json("roomId","r1","organiser","ivan",
                    "date","2026-11-06","start","09:00","end","10:00",
                    "attendees","[\"a\",\"b\",\"c\",\"d\",\"e\"]"));
            check(r.statusCode() == 422, "status 422 — capacity exceeded");
        });

        test("M3 allow within capacity (Atlas=4, 4 attendees)", () -> {
            var r = post(BASE, json("roomId","r1","organiser","judy",
                    "date","2026-11-06","start","09:00","end","10:00",
                    "attendees","[\"a\",\"b\",\"c\",\"d\"]"));
            check(r.statusCode() == 201, "status 201 — within capacity");
        });

        // M4: Find slot
        test("M4 find-slot on empty day", () -> {
            var r = post(BASE + "/find-slot",
                    "{\"durationMinutes\":60,\"attendeeCount\":5,\"date\":\"2026-12-01\"}");
            check(r.statusCode() == 200, "status 200");
            check(r.body().contains("\"found\":true"), "slot found");
            check(r.body().contains("\"startTime\":\"09:00\""), "earliest is 09:00");
        });

        test("M4 find-slot with some rooms busy", () -> {
            post(BASE, json("roomId","r2","organiser","ken",
                    "date","2026-12-02","start","09:00","end","11:00",
                    "attendees","[\"ken\"]"));
            post(BASE, json("roomId","r3","organiser","lena",
                    "date","2026-12-02","start","09:00","end","10:00",
                    "attendees","[\"lena\"]"));

            var r = post(BASE + "/find-slot",
                    "{\"durationMinutes\":30,\"attendeeCount\":5,\"date\":\"2026-12-02\"}");
            check(r.body().contains("\"roomId\":\"r4\""), "picks free r4 (cap 20)");
            check(r.body().contains("\"startTime\":\"09:00\""), "earliest is 09:00");
        });

        test("M4 find-slot no room big enough", () -> {
            var r = post(BASE + "/find-slot",
                    "{\"durationMinutes\":60,\"attendeeCount\":999,\"date\":\"2026-12-03\"}");
            check(r.body().contains("\"found\":false"), "no room fits 999 people");
        });

        // M5: Recurring
        test("M5 weekly recurring — all clean", () -> {
            var r = post(BASE + "/recurring", json(
                    "roomId","r3","organiser","mike",
                    "startDate","2026-11-09","endDate","2026-11-23",
                    "start","14:00","end","15:00",
                    "attendees","[\"mike\",\"nina\"]"));
            check(r.statusCode() == 201, "status 201");
            check(r.body().contains("\"successful\":[{"), "has successful");
            check(r.body().contains("\"conflicts\":[]"), "no conflicts");
        });

        test("M5 weekly recurring with partial conflict", () -> {
            // pre-book a single that conflicts with one week
            post(BASE, json("roomId","r4","organiser","oli",
                    "date","2026-11-16","start","14:00","end","15:00",
                    "attendees","[\"oli\"]"));

            var r = post(BASE + "/recurring", json(
                    "roomId","r4","organiser","pam",
                    "startDate","2026-11-09","endDate","2026-11-23",
                    "start","14:00","end","15:00",
                    "attendees","[\"pam\"]"));
            check(r.statusCode() == 201, "status 201");
            check(r.body().contains("\"conflicts\":"), "has conflicts section");
        });

        // Edge cases
        test("Validation: missing fields → 400", () -> {
            var r = post(BASE, "{\"roomId\":\"r1\",\"organiser\":\"test\"}");
            check(r.statusCode() == 400, "status 400");
        });

        test("Validation: end before start → 400", () -> {
            var r = post(BASE, json("roomId","r2","organiser","test",
                    "date","2026-11-01","start","15:00","end","14:00",
                    "attendees","[\"test\"]"));
            check(r.statusCode() == 400, "status 400");
        });

        test("Validation: outside 09:00-18:00 → 400", () -> {
            var r = post(BASE, json("roomId","r2","organiser","test",
                    "date","2026-11-01","start","08:00","end","09:00",
                    "attendees","[\"test\"]"));
            check(r.statusCode() == 400, "status 400");
        });

        test("Validation: unknown room → 404", () -> {
            var r = post(BASE, json("roomId","r99","organiser","test",
                    "date","2026-11-01","start","10:00","end","11:00",
                    "attendees","[\"test\"]"));
            check(r.statusCode() == 404, "status 404");
        });

        System.out.println("\n===== " + passed + " passed, " + failed + " failed =====\n");
        if (failed > 0) System.exit(1);
    }

    // --- HTTP helpers ---

    static HttpResponse<String> post(String url, String body) throws Exception {
        var req = HttpRequest.newBuilder(URI.create(url))
                .POST(BodyPublishers.ofString(body))
                .header("Content-Type", "application/json")
                .timeout(Duration.ofSeconds(5)).build();
        return client.send(req, BodyHandlers.ofString());
    }

    static HttpResponse<String> put(String url, String body) throws Exception {
        var req = HttpRequest.newBuilder(URI.create(url))
                .PUT(BodyPublishers.ofString(body))
                .header("Content-Type", "application/json")
                .timeout(Duration.ofSeconds(5)).build();
        return client.send(req, BodyHandlers.ofString());
    }

    static HttpResponse<String> get(String url) throws Exception {
        var req = HttpRequest.newBuilder(URI.create(url))
                .GET().timeout(Duration.ofSeconds(5)).build();
        return client.send(req, BodyHandlers.ofString());
    }

    static HttpResponse<String> delete(String url) throws Exception {
        var req = HttpRequest.newBuilder(URI.create(url))
                .DELETE().timeout(Duration.ofSeconds(5)).build();
        return client.send(req, BodyHandlers.ofString());
    }

    // --- Helpers ---

    static String json(String... kv) {
        var sb = new StringBuilder("{");
        for (int i = 0; i < kv.length; i += 2) {
            if (i > 0) sb.append(",");
            sb.append("\"").append(kv[i]).append("\":").append(kv[i + 1]);
        }
        return sb.append("}").toString();
    }

    static String extractId(String json) {
        int s = json.indexOf("\"id\":\"") + 6;
        return json.substring(s, json.indexOf("\"", s));
    }

    interface ThrowingRunnable { void run() throws Exception; }

    static void test(String name, ThrowingRunnable r) {
        try {
            r.run();
            System.out.println("  ✓ " + name);
            passed++;
        } catch (AssertionError | Exception e) {
            System.out.println("  ✗ " + name + " — " + e.getMessage());
            failed++;
        }
    }

    static void check(boolean cond, String msg) {
        if (!cond) throw new AssertionError(msg);
    }
}