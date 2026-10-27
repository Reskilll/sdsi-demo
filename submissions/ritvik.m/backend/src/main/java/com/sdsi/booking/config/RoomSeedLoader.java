package com.sdsi.booking.config;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sdsi.booking.domain.Room;
import com.sdsi.booking.repo.RoomRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.io.Resource;
import org.springframework.core.io.ResourceLoader;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.io.InputStream;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Seeds the room catalogue from {@code rooms.json} on startup. Existing rooms
 * are left untouched so locally changed data is never overwritten.
 */
@Component
public class RoomSeedLoader implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(RoomSeedLoader.class);
    private static final Pattern ROOM_ID = Pattern.compile("[a-z0-9][a-z0-9-]{0,39}");

    private final RoomRepository roomRepository;
    private final ObjectMapper objectMapper;
    private final ResourceLoader resourceLoader;
    private final AppProperties properties;

    public RoomSeedLoader(RoomRepository roomRepository, ObjectMapper objectMapper,
                          ResourceLoader resourceLoader, AppProperties properties) {
        this.roomRepository = roomRepository;
        this.objectMapper = objectMapper;
        this.resourceLoader = resourceLoader;
        this.properties = properties;
    }

    @Override
    @Transactional
    public void run(ApplicationArguments args) throws Exception {
        Resource resource = resourceLoader.getResource(properties.seed().roomsResource());
        if (!resource.exists()) {
            throw new IllegalStateException("Room seed resource not found: " + properties.seed().roomsResource());
        }
        List<RoomSeed> seeds;
        try (InputStream input = resource.getInputStream()) {
            seeds = objectMapper.readValue(input, new TypeReference<List<RoomSeed>>() {
            });
        }

        Set<String> ids = new HashSet<>();
        int inserted = 0;
        for (RoomSeed seed : seeds) {
            validate(seed, ids);
            if (roomRepository.existsById(seed.id())) {
                continue;
            }
            Set<String> amenities = new LinkedHashSet<>();
            if (seed.amenities() != null) {
                seed.amenities().stream()
                        .filter(a -> a != null && !a.isBlank())
                        .map(a -> a.trim().toLowerCase(Locale.ROOT))
                        .forEach(amenities::add);
            }
            roomRepository.save(new Room(seed.id(), seed.name().trim(), seed.capacity(),
                    seed.floor(), seed.location(), amenities));
            inserted++;
        }
        log.info("Room catalogue ready: {} room(s) present, {} seeded from {}", roomRepository.count(),
                inserted, properties.seed().roomsResource());
    }

    private void validate(RoomSeed seed, Set<String> ids) {
        if (seed == null || seed.id() == null || !ROOM_ID.matcher(seed.id()).matches()) {
            throw new IllegalStateException("rooms.json contains an invalid room id: " + (seed == null ? null : seed.id()));
        }
        if (!ids.add(seed.id())) {
            throw new IllegalStateException("rooms.json contains duplicate room id: " + seed.id());
        }
        if (seed.name() == null || seed.name().isBlank() || seed.name().length() > 80) {
            throw new IllegalStateException("rooms.json: room " + seed.id() + " has an invalid name");
        }
        if (seed.capacity() == null || seed.capacity() < 1) {
            throw new IllegalStateException("rooms.json: room " + seed.id() + " has an invalid capacity");
        }
    }

    record RoomSeed(String id, String name, Integer capacity, Integer floor, String location,
                    List<String> amenities) {
    }
}
