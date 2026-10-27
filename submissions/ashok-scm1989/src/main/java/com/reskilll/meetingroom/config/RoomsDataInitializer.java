package com.reskilll.meetingroom.config;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.reskilll.meetingroom.model.Room;
import com.reskilll.meetingroom.repository.RoomRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.core.io.Resource;
import org.springframework.core.io.ResourceLoader;
import org.springframework.stereotype.Component;

import java.io.File;
import java.io.InputStream;
import java.util.List;

@Component
public class RoomsDataInitializer implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(RoomsDataInitializer.class);

    private final RoomRepository roomRepository;
    private final ObjectMapper objectMapper;
    private final ResourceLoader resourceLoader;

    @Value("${app.rooms-file:classpath:data/rooms.json}")
    private String roomsFilePath;

    public RoomsDataInitializer(RoomRepository roomRepository, ObjectMapper objectMapper, ResourceLoader resourceLoader) {
        this.roomRepository = roomRepository;
        this.objectMapper = objectMapper;
        this.resourceLoader = resourceLoader;
    }

    @Override
    public void run(String... args) {
        loadRooms();
    }

    public synchronized void loadRooms() {
        try {
            InputStream inputStream = null;

            // Try configured resource path (e.g. classpath:data/rooms.json)
            Resource resource = resourceLoader.getResource(roomsFilePath);
            if (resource.exists()) {
                inputStream = resource.getInputStream();
            } else {
                // Try fallback filesystem path: ./data/rooms.json
                File file = new File("data/rooms.json");
                if (file.exists()) {
                    inputStream = file.toURI().toURL().openStream();
                }
            }

            if (inputStream != null) {
                try (InputStream is = inputStream) {
                    List<Room> rooms = objectMapper.readValue(is, new TypeReference<List<Room>>() {});
                    roomRepository.saveAll(rooms);
                    log.info("Successfully loaded {} meeting rooms into repository", rooms.size());
                    rooms.forEach(r -> log.info("  - Room [{}]: '{}', Capacity: {}, Floor: {}, Amenities: {}",
                            r.getId(), r.getName(), r.getCapacity(), r.getFloor(), r.getAmenities()));
                }
            } else {
                log.warn("Could not find rooms.json at {} or ./data/rooms.json. Seeding defaults.", roomsFilePath);
                seedDefaults();
            }
        } catch (Exception e) {
            log.error("Failed to load rooms from {}: {}. Seeding defaults.", roomsFilePath, e.getMessage());
            seedDefaults();
        }
    }

    private void seedDefaults() {
        List<Room> defaults = List.of(
                new Room("ROOM-101", "Ada Lovelace Focus Room", 4, 1, List.of("WHITEBOARD", "WIFI")),
                new Room("ROOM-102", "Alan Turing Huddle Room", 8, 1, List.of("PROJECTOR", "WHITEBOARD", "VIDEO_CONFERENCE")),
                new Room("ROOM-201", "Grace Hopper Conference Room", 12, 2, List.of("PROJECTOR", "WHITEBOARD", "VIDEO_CONFERENCE")),
                new Room("ROOM-301", "Margaret Hamilton Boardroom", 24, 3, List.of("4K_DISPLAY", "VIDEO_CONFERENCE", "WHITEBOARD", "PODIUM")),
                new Room("ROOM-PHONE-1", "Claude Shannon Phone Booth", 2, 1, List.of("ACOUSTIC_PANEL"))
        );
        roomRepository.saveAll(defaults);
        log.info("Seeded {} default rooms into repository", defaults.size());
    }
}
