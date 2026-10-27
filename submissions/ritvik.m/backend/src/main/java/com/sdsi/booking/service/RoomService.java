package com.sdsi.booking.service;

import com.sdsi.booking.domain.Room;
import com.sdsi.booking.repo.RoomRepository;
import com.sdsi.booking.web.dto.RoomResponse;
import com.sdsi.booking.web.error.NotFoundException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class RoomService {

    private final RoomRepository roomRepository;
    private final BookingMapper mapper;

    public RoomService(RoomRepository roomRepository, BookingMapper mapper) {
        this.roomRepository = roomRepository;
        this.mapper = mapper;
    }

    @Transactional(readOnly = true)
    public List<RoomResponse> list() {
        return roomRepository.findByActiveTrueOrderByCapacityAscNameAsc().stream()
                .map(mapper::toRoom)
                .toList();
    }

    @Transactional(readOnly = true)
    public RoomResponse get(String id) {
        return mapper.toRoom(requireActive(id));
    }

    public Room requireActive(String id) {
        return roomRepository.findByIdAndActiveTrue(id)
                .orElseThrow(() -> new NotFoundException("Room", id));
    }
}
