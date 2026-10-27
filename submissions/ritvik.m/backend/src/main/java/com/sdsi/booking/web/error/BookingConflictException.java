package com.sdsi.booking.web.error;

import com.sdsi.booking.web.dto.ConflictView;
import org.springframework.http.HttpStatus;

import java.util.List;

public class BookingConflictException extends ApiException {

    private final transient List<ConflictView> conflicts;

    public BookingConflictException(List<ConflictView> conflicts) {
        super(HttpStatus.CONFLICT, "BOOKING_CONFLICT",
                "The requested slot overlaps " + conflicts.size() + " existing booking(s) in this room.");
        this.conflicts = List.copyOf(conflicts);
    }

    public List<ConflictView> getConflicts() {
        return conflicts;
    }
}
