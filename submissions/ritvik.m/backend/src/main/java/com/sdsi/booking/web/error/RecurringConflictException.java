package com.sdsi.booking.web.error;

import com.sdsi.booking.web.dto.OccurrenceView;
import org.springframework.http.HttpStatus;

import java.util.List;

public class RecurringConflictException extends ApiException {

    private final transient List<OccurrenceView> occurrences;

    public RecurringConflictException(List<OccurrenceView> occurrences, int conflictCount, int occurrenceCount) {
        super(HttpStatus.CONFLICT, "RECURRING_CONFLICT",
                conflictCount + " of " + occurrenceCount
                        + " occurrence(s) conflict with existing bookings; no series was created.");
        this.occurrences = List.copyOf(occurrences);
    }

    public List<OccurrenceView> getOccurrences() {
        return occurrences;
    }
}
