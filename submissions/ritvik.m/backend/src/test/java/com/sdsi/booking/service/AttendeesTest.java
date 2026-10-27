package com.sdsi.booking.service;

import com.sdsi.booking.web.error.RuleViolationException;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class AttendeesTest {

    @Test
    void derivesCountFromTheList() {
        Attendees.AttendeeData data = Attendees.resolve(null, List.of(" Ada ", "Grace"));
        assertThat(data.count()).isEqualTo(2);
        assertThat(data.names()).containsExactly("Ada", "Grace");
    }

    @Test
    void acceptsMatchingCountAndList() {
        Attendees.AttendeeData data = Attendees.resolve(2, List.of("Ada", "Grace"));
        assertThat(data.count()).isEqualTo(2);
    }

    @Test
    void deduplicatesNamesOnCaseSensitiveBasis() {
        Attendees.AttendeeData data = Attendees.resolve(null, List.of("Ada", "ada", "Ada"));
        assertThat(data.count()).isEqualTo(2);
        assertThat(data.names()).containsExactly("Ada", "ada");
    }

    @Test
    void rejectsMismatch() {
        assertThatThrownBy(() -> Attendees.resolve(3, List.of("Ada", "Grace")))
                .extracting("code").isEqualTo("ATTENDEE_COUNT_MISMATCH");
    }

    @Test
    void rejectsMissingAttendees() {
        assertThatThrownBy(() -> Attendees.resolve(null, List.of()))
                .extracting("code").isEqualTo("ATTENDEES_REQUIRED");
        assertThatThrownBy(() -> Attendees.resolve(null, null))
                .isInstanceOf(RuleViolationException.class);
    }

    @Test
    void capacityCheckUsesTheEffectiveCount() {
        Attendees.AttendeeData data = new Attendees.AttendeeData(5, Set.of("a", "b", "c", "d", "e"));
        assertThatThrownBy(() -> Attendees.checkCapacity(data, "Atlas", 4))
                .extracting("code").isEqualTo("CAPACITY_EXCEEDED");

        Attendees.AttendeeData fits = new Attendees.AttendeeData(4, Set.of());
        org.assertj.core.api.Assertions.assertThatCode(
                () -> Attendees.checkCapacity(fits, "Atlas", 4)).doesNotThrowAnyException();
    }
}
