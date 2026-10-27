package com.sdsi.booking.config;

import com.sdsi.booking.domain.Room;
import com.sdsi.booking.repository.RoomRepository;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Configuration
public class SeedDataConfig {

    @Bean
    ApplicationRunner seedRooms(RoomRepository rooms) {
        return args -> seed(rooms);
    }

    @Transactional
    void seed(RoomRepository rooms) {
        if (rooms.count() > 0) {
            return;
        }
        rooms.saveAll(List.of(
                new Room("Room A", 5),
                new Room("Room B", 10),
                new Room("Room C", 20)
        ));
    }
}
