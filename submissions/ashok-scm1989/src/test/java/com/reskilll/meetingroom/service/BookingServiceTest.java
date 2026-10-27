package com.reskilll.meetingroom.service;

import com.reskilll.meetingroom.dto.*;
import com.reskilll.meetingroom.exception.BookingConflictException;
import com.reskilll.meetingroom.exception.CapacityExceededException;
import com.reskilll.meetingroom.exception.InvalidBookingException;
import com.reskilll.meetingroom.exception.ResourceNotFoundException;
import com.reskilll.meetingroom.model.Booking;
import com.reskilll.meetingroom.model.RecurrencePolicy;
import com.reskilll.meetingroom.model.Room;
import com.reskilll.meetingroom.repository.BookingRepository;
import com.reskilll.meetingroom.repository.RoomRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.annotation.DirtiesContext;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@SpringBootTest
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_EACH_TEST_METHOD)
class BookingServiceTest {

    @Autowired
    private BookingService bookingService;

    @Autowired
    private RoomRepository roomRepository;

    @Autowired
    private BookingRepository bookingRepository;

    private final LocalDate testDate = LocalDate.of(2026, 11, 2); // Monday

    @BeforeEach
    void setUp() {
        bookingRepository.deleteAll();
        roomRepository.clear();

        roomRepository.saveAll(List.of(
                new Room("ROOM-101", "Focus Room 1", 4, 1, List.of("WHITEBOARD")),
                new Room("ROOM-102", "Huddle Room 2", 8, 1, List.of("WHITEBOARD", "PROJECTOR")),
                new Room("ROOM-201", "Conference Room 3", 12, 2, List.of("VIDEO_CONFERENCE")),
                new Room("BOARDROOM", "Executive Boardroom", 24, 3, List.of("VIDEO_CONFERENCE", "4K_DISPLAY"))
        ));
    }

    @Nested
    @DisplayName("M1: CRUD Bookings")
    class Milestone1CrudTests {

        @Test
        @DisplayName("Create booking succeeds with valid parameters")
        void createBooking_success() {
            CreateBookingRequest req = new CreateBookingRequest(
                    "ROOM-101", "Sprint Review", "alice@example.com",
                    testDate.atTime(10, 0), testDate.atTime(11, 0),
                    List.of("bob@example.com", "charlie@example.com")
            );

            BookingResponse response = bookingService.createBooking(req);

            assertThat(response.getId()).isNotNull().startsWith("BKG-");
            assertThat(response.getRoomId()).isEqualTo("ROOM-101");
            assertThat(response.getTitle()).isEqualTo("Sprint Review");
            assertThat(response.getOrganiser()).isEqualTo("alice@example.com");
            assertThat(response.getStartTime()).isEqualTo(testDate.atTime(10, 0));
            assertThat(response.getEndTime()).isEqualTo(testDate.atTime(11, 0));
            assertThat(response.getAttendeeCount()).isEqualTo(2);
        }

        @Test
        @DisplayName("Read booking by ID returns accurate details")
        void getBooking_success() {
            CreateBookingRequest req = new CreateBookingRequest(
                    "ROOM-101", "1-on-1", "alice@example.com",
                    testDate.atTime(9, 0), testDate.atTime(10, 0),
                    List.of("bob@example.com")
            );
            BookingResponse created = bookingService.createBooking(req);

            BookingResponse fetched = bookingService.getBooking(created.getId());
            assertThat(fetched.getId()).isEqualTo(created.getId());
            assertThat(fetched.getTitle()).isEqualTo("1-on-1");
        }

        @Test
        @DisplayName("Read non-existent booking throws ResourceNotFoundException")
        void getBooking_notFound() {
            assertThatThrownBy(() -> bookingService.getBooking("NON-EXISTENT"))
                    .isInstanceOf(ResourceNotFoundException.class)
                    .hasMessageContaining("Booking not found");
        }

        @Test
        @DisplayName("Update booking changes fields and validates capacity & overlap")
        void updateBooking_success() {
            CreateBookingRequest req = new CreateBookingRequest(
                    "ROOM-101", "Initial Title", "alice@example.com",
                    testDate.atTime(14, 0), testDate.atTime(15, 0),
                    List.of("bob@example.com")
            );
            BookingResponse created = bookingService.createBooking(req);

            UpdateBookingRequest updateReq = new UpdateBookingRequest();
            updateReq.setTitle("Updated Title");
            updateReq.setStartTime(testDate.atTime(14, 30));
            updateReq.setEndTime(testDate.atTime(15, 30));

            BookingResponse updated = bookingService.updateBooking(created.getId(), updateReq);
            assertThat(updated.getTitle()).isEqualTo("Updated Title");
            assertThat(updated.getStartTime()).isEqualTo(testDate.atTime(14, 30));
            assertThat(updated.getEndTime()).isEqualTo(testDate.atTime(15, 30));
        }

        @Test
        @DisplayName("Delete booking removes entity from database")
        void deleteBooking_success() {
            CreateBookingRequest req = new CreateBookingRequest(
                    "ROOM-101", "To Delete", "alice@example.com",
                    testDate.atTime(16, 0), testDate.atTime(17, 0),
                    List.of("bob@example.com")
            );
            BookingResponse created = bookingService.createBooking(req);

            bookingService.deleteBooking(created.getId());

            assertThatThrownBy(() -> bookingService.getBooking(created.getId()))
                    .isInstanceOf(ResourceNotFoundException.class);
        }
    }

    @Nested
    @DisplayName("M2: Overlap Rejection & Back-to-Back Bookings")
    class Milestone2OverlapTests {

        @BeforeEach
        void createBaselineBooking() {
            // Baseline booking in ROOM-101: 10:00 to 11:30
            bookingService.createBooking(new CreateBookingRequest(
                    "ROOM-101", "Baseline Booking", "alice@example.com",
                    testDate.atTime(10, 0), testDate.atTime(11, 30),
                    List.of("alice@example.com")
            ));
        }

        @Test
        @DisplayName("Reject booking with exact same time slot")
        void reject_exactDuplicate() {
            CreateBookingRequest clash = new CreateBookingRequest(
                    "ROOM-101", "Clash", "bob@example.com",
                    testDate.atTime(10, 0), testDate.atTime(11, 30),
                    List.of("bob@example.com")
            );

            assertThatThrownBy(() -> bookingService.createBooking(clash))
                    .isInstanceOf(BookingConflictException.class)
                    .hasMessageContaining("already booked");
        }

        @Test
        @DisplayName("Reject booking starting inside existing interval")
        void reject_startsInside() {
            CreateBookingRequest clash = new CreateBookingRequest(
                    "ROOM-101", "Starts Inside", "bob@example.com",
                    testDate.atTime(10, 30), testDate.atTime(12, 0),
                    List.of("bob@example.com")
            );

            assertThatThrownBy(() -> bookingService.createBooking(clash))
                    .isInstanceOf(BookingConflictException.class);
        }

        @Test
        @DisplayName("Reject booking ending inside existing interval")
        void reject_endsInside() {
            CreateBookingRequest clash = new CreateBookingRequest(
                    "ROOM-101", "Ends Inside", "bob@example.com",
                    testDate.atTime(9, 30), testDate.atTime(10, 30),
                    List.of("bob@example.com")
            );

            assertThatThrownBy(() -> bookingService.createBooking(clash))
                    .isInstanceOf(BookingConflictException.class);
        }

        @Test
        @DisplayName("Reject booking completely enclosing existing interval")
        void reject_enclosesExisting() {
            CreateBookingRequest clash = new CreateBookingRequest(
                    "ROOM-101", "Enclosing", "bob@example.com",
                    testDate.atTime(9, 0), testDate.atTime(12, 0),
                    List.of("bob@example.com")
            );

            assertThatThrownBy(() -> bookingService.createBooking(clash))
                    .isInstanceOf(BookingConflictException.class);
        }

        @Test
        @DisplayName("Allow back-to-back booking immediately before existing (09:00 - 10:00)")
        void allow_backToBackBefore() {
            CreateBookingRequest before = new CreateBookingRequest(
                    "ROOM-101", "Before Slot", "carol@example.com",
                    testDate.atTime(9, 0), testDate.atTime(10, 0),
                    List.of("carol@example.com")
            );

            BookingResponse response = bookingService.createBooking(before);
            assertThat(response.getId()).isNotNull();
            assertThat(response.getEndTime()).isEqualTo(testDate.atTime(10, 0));
        }

        @Test
        @DisplayName("Allow back-to-back booking immediately after existing (11:30 - 12:30)")
        void allow_backToBackAfter() {
            CreateBookingRequest after = new CreateBookingRequest(
                    "ROOM-101", "After Slot", "dave@example.com",
                    testDate.atTime(11, 30), testDate.atTime(12, 30),
                    List.of("dave@example.com")
            );

            BookingResponse response = bookingService.createBooking(after);
            assertThat(response.getId()).isNotNull();
            assertThat(response.getStartTime()).isEqualTo(testDate.atTime(11, 30));
        }

        @Test
        @DisplayName("Allow same time interval on a DIFFERENT room")
        void allow_differentRoomSameTime() {
            CreateBookingRequest diffRoom = new CreateBookingRequest(
                    "ROOM-102", "Diff Room", "eve@example.com",
                    testDate.atTime(10, 0), testDate.atTime(11, 30),
                    List.of("eve@example.com")
            );

            BookingResponse response = bookingService.createBooking(diffRoom);
            assertThat(response.getId()).isNotNull();
            assertThat(response.getRoomId()).isEqualTo("ROOM-102");
        }
    }

    @Nested
    @DisplayName("M3: Capacity Check")
    class Milestone3CapacityTests {

        @Test
        @DisplayName("Reject booking when attendees exceed room capacity")
        void reject_capacityExceeded() {
            // ROOM-101 capacity is 4; request 5 attendees
            CreateBookingRequest req = new CreateBookingRequest(
                    "ROOM-101", "Large Meeting", "alice@example.com",
                    testDate.atTime(13, 0), testDate.atTime(14, 0),
                    List.of("a@ex.com", "b@ex.com", "c@ex.com", "d@ex.com", "e@ex.com")
            );

            assertThatThrownBy(() -> bookingService.createBooking(req))
                    .isInstanceOf(CapacityExceededException.class)
                    .hasMessageContaining("capacity 4, but 5 attendees were requested");
        }

        @Test
        @DisplayName("Accept booking when attendees exactly match room capacity")
        void accept_exactCapacity() {
            // ROOM-101 capacity is 4; request 4 attendees
            CreateBookingRequest req = new CreateBookingRequest(
                    "ROOM-101", "Exact Match", "alice@example.com",
                    testDate.atTime(13, 0), testDate.atTime(14, 0),
                    List.of("a@ex.com", "b@ex.com", "c@ex.com", "d@ex.com")
            );

            BookingResponse response = bookingService.createBooking(req);
            assertThat(response.getAttendeeCount()).isEqualTo(4);
        }

        @Test
        @DisplayName("Reject booking for non-existent room")
        void reject_unknownRoom() {
            CreateBookingRequest req = new CreateBookingRequest(
                    "ROOM-999", "Ghost Room", "alice@example.com",
                    testDate.atTime(13, 0), testDate.atTime(14, 0),
                    List.of("alice@example.com")
            );

            assertThatThrownBy(() -> bookingService.createBooking(req))
                    .isInstanceOf(ResourceNotFoundException.class)
                    .hasMessageContaining("Room not found");
        }
    }

    @Nested
    @DisplayName("M4: Find-Slot Algorithm")
    class Milestone4FindSlotTests {

        @Test
        @DisplayName("Return 09:00 slot on empty day using smallest eligible room (best-fit)")
        void findSlot_emptyDay_bestFitRoom() {
            // 6 attendees: ROOM-102 has cap 8, ROOM-201 has cap 12, BOARDROOM has cap 24
            // Should pick ROOM-102 at 09:00:00!
            SlotRecommendation slot = bookingService.findEarliestSlot(testDate, 60, 6);

            assertThat(slot.getRoomId()).isEqualTo("ROOM-102");
            assertThat(slot.getStartTime()).isEqualTo(testDate.atTime(9, 0));
            assertThat(slot.getEndTime()).isEqualTo(testDate.atTime(10, 0));
        }

        @Test
        @DisplayName("Find earliest slot when 09:00 to 10:00 is booked across all rooms")
        void findSlot_partiallyBooked() {
            // Book 09:00 - 10:00 in ROOM-101, ROOM-102, ROOM-201, BOARDROOM
            for (String rid : List.of("ROOM-101", "ROOM-102", "ROOM-201", "BOARDROOM")) {
                bookingService.createBooking(new CreateBookingRequest(
                        rid, "Morning Sync", "lead@example.com",
                        testDate.atTime(9, 0), testDate.atTime(10, 0),
                        List.of("lead@example.com")
                ));
            }

            // Next available slot should be at 10:00:00
            SlotRecommendation slot = bookingService.findEarliestSlot(testDate, 30, 4);

            assertThat(slot.getStartTime()).isEqualTo(testDate.atTime(10, 0));
            assertThat(slot.getEndTime()).isEqualTo(testDate.atTime(10, 30));
        }

        @Test
        @DisplayName("Pick room that is free earlier than another room")
        void findSlot_earliestStartTimePreferred() {
            // ROOM-102 is booked 09:00 to 11:00
            bookingService.createBooking(new CreateBookingRequest(
                    "ROOM-102", "Blocker", "lead@example.com",
                    testDate.atTime(9, 0), testDate.atTime(11, 0),
                    List.of("lead@example.com")
            ));
            // ROOM-201 is free from 09:00!
            SlotRecommendation slot = bookingService.findEarliestSlot(testDate, 60, 6);

            // Should select ROOM-201 because it has the earlier slot at 09:00
            assertThat(slot.getRoomId()).isEqualTo("ROOM-201");
            assertThat(slot.getStartTime()).isEqualTo(testDate.atTime(9, 0));
        }

        @Test
        @DisplayName("Find slot in gap between two existing bookings")
        void findSlot_inBetweenGap() {
            // In ROOM-102:
            // Booking 1: 09:00 - 10:00
            // Booking 2: 11:30 - 18:00
            // Gap is 10:00 - 11:30 (90 mins). Search for 60 mins -> starts at 10:00
            bookingService.createBooking(new CreateBookingRequest(
                    "ROOM-102", "Booking 1", "u1@example.com",
                    testDate.atTime(9, 0), testDate.atTime(10, 0),
                    List.of("u1@example.com")
            ));
            bookingService.createBooking(new CreateBookingRequest(
                    "ROOM-102", "Booking 2", "u2@example.com",
                    testDate.atTime(11, 30), testDate.atTime(18, 0),
                    List.of("u2@example.com")
            ));

            // Also fill ROOM-201 and BOARDROOM completely for this test
            bookingService.createBooking(new CreateBookingRequest(
                    "ROOM-201", "Full", "u3@example.com",
                    testDate.atTime(9, 0), testDate.atTime(18, 0),
                    List.of("u3@example.com")
            ));
            bookingService.createBooking(new CreateBookingRequest(
                    "BOARDROOM", "Full", "u4@example.com",
                    testDate.atTime(9, 0), testDate.atTime(18, 0),
                    List.of("u4@example.com")
            ));

            SlotRecommendation slot = bookingService.findEarliestSlot(testDate, 60, 6);
            assertThat(slot.getRoomId()).isEqualTo("ROOM-102");
            assertThat(slot.getStartTime()).isEqualTo(testDate.atTime(10, 0));
            assertThat(slot.getEndTime()).isEqualTo(testDate.atTime(11, 0));
        }

        @Test
        @DisplayName("Throw exception if no room fits the attendee count")
        void findSlot_noRoomLargeEnough() {
            assertThatThrownBy(() -> bookingService.findEarliestSlot(testDate, 30, 100))
                    .isInstanceOf(ResourceNotFoundException.class)
                    .hasMessageContaining("No room available with capacity for 100 attendees");
        }
    }

    @Nested
    @DisplayName("M5: Weekly Recurring Bookings")
    class Milestone5RecurringTests {

        @Test
        @DisplayName("All 4 occurrences created when no conflicts exist")
        void recurring_allClear() {
            RecurringBookingRequest req = new RecurringBookingRequest(
                    "ROOM-102", "Weekly Sprint", "pm@example.com",
                    testDate.atTime(14, 0), testDate.atTime(15, 0),
                    List.of("dev1@example.com", "dev2@example.com"),
                    4,
                    RecurrencePolicy.BOOK_AVAILABLE
            );

            RecurringBookingResult result = bookingService.createRecurringBooking(req);

            assertThat(result.getTotalRequested()).isEqualTo(4);
            assertThat(result.getSuccessfulCount()).isEqualTo(4);
            assertThat(result.getConflictCount()).isEqualTo(0);
            assertThat(result.getConflicts()).isEmpty();
            assertThat(result.getSuccessfulBookings()).hasSize(4);

            // Verify dates are 7 days apart
            List<BookingResponse> bookings = result.getSuccessfulBookings();
            assertThat(bookings.get(0).getStartTime()).isEqualTo(testDate.atTime(14, 0));
            assertThat(bookings.get(1).getStartTime()).isEqualTo(testDate.plusWeeks(1).atTime(14, 0));
            assertThat(bookings.get(2).getStartTime()).isEqualTo(testDate.plusWeeks(2).atTime(14, 0));
            assertThat(bookings.get(3).getStartTime()).isEqualTo(testDate.plusWeeks(3).atTime(14, 0));
        }

        @Test
        @DisplayName("Report conflict on occurrence 2 when week 2 is already booked (BOOK_AVAILABLE)")
        void recurring_withConflict_bookAvailable() {
            // Block week 2 (index 2): testDate.plusWeeks(1)
            LocalDateTime blockerStart = testDate.plusWeeks(1).atTime(14, 0);
            LocalDateTime blockerEnd = testDate.plusWeeks(1).atTime(15, 0);
            BookingResponse blocker = bookingService.createBooking(new CreateBookingRequest(
                    "ROOM-102", "Pre-existing Client Call", "client@example.com",
                    blockerStart, blockerEnd,
                    List.of("client@example.com")
            ));

            RecurringBookingRequest req = new RecurringBookingRequest(
                    "ROOM-102", "Weekly Sync", "team@example.com",
                    testDate.atTime(14, 0), testDate.atTime(15, 0),
                    List.of("team1@example.com"),
                    4,
                    RecurrencePolicy.BOOK_AVAILABLE
            );

            RecurringBookingResult result = bookingService.createRecurringBooking(req);

            assertThat(result.getTotalRequested()).isEqualTo(4);
            assertThat(result.getSuccessfulCount()).isEqualTo(3);
            assertThat(result.getConflictCount()).isEqualTo(1);

            OccurrenceConflict conflict = result.getConflicts().get(0);
            assertThat(conflict.getOccurrenceIndex()).isEqualTo(2);
            assertThat(conflict.getDate()).isEqualTo(testDate.plusWeeks(1));
            assertThat(conflict.getConflictingBookingId()).isEqualTo(blocker.getId());
            assertThat(conflict.getConflictingOrganiser()).isEqualTo("client@example.com");
        }

        @Test
        @DisplayName("ALL_OR_NOTHING policy persists zero bookings when a conflict exists")
        void recurring_allOrNothing_abortsOnConflict() {
            // Pre-book week 3
            bookingService.createBooking(new CreateBookingRequest(
                    "ROOM-102", "Roadblock", "boss@example.com",
                    testDate.plusWeeks(2).atTime(10, 0), testDate.plusWeeks(2).atTime(11, 0),
                    List.of("boss@example.com")
            ));

            RecurringBookingRequest req = new RecurringBookingRequest(
                    "ROOM-102", "Important Series", "team@example.com",
                    testDate.atTime(10, 0), testDate.atTime(11, 0),
                    List.of("dev@example.com"),
                    4,
                    RecurrencePolicy.ALL_OR_NOTHING
            );

            RecurringBookingResult result = bookingService.createRecurringBooking(req);

            assertThat(result.getSuccessfulCount()).isEqualTo(0);
            assertThat(result.getConflictCount()).isEqualTo(1);
            assertThat(result.getSuccessfulBookings()).isEmpty();
            assertThat(result.getConflicts()).hasSize(1);
            assertThat(result.getConflicts().get(0).getOccurrenceIndex()).isEqualTo(3);
        }

        @Test
        @DisplayName("Delete recurring series by group ID deletes all occurrences")
        void deleteRecurringGroup_success() {
            RecurringBookingRequest req = new RecurringBookingRequest(
                    "ROOM-201", "Team All-Hands", "hr@example.com",
                    testDate.atTime(11, 0), testDate.atTime(12, 0),
                    List.of("all@example.com"),
                    3,
                    RecurrencePolicy.BOOK_AVAILABLE
            );

            RecurringBookingResult result = bookingService.createRecurringBooking(req);
            String groupId = result.getRecurrenceGroupId();

            long deleted = bookingService.deleteRecurringGroup(groupId);
            assertThat(deleted).isEqualTo(3);

            // Confirm none exist in DB
            List<BookingResponse> remaining = bookingService.listBookings("ROOM-201", null, null);
            assertThat(remaining).isEmpty();
        }
    }

    @Nested
    @DisplayName("Edge Cases & Robustness")
    class EdgeCaseTests {

        @Test
        @DisplayName("Reject booking where start time is equal to end time (0 duration)")
        void reject_zeroDuration() {
            CreateBookingRequest req = new CreateBookingRequest(
                    "ROOM-101", "Zero Duration", "alice@example.com",
                    testDate.atTime(10, 0), testDate.atTime(10, 0),
                    List.of("alice@example.com")
            );

            assertThatThrownBy(() -> bookingService.createBooking(req))
                    .isInstanceOf(InvalidBookingException.class)
                    .hasMessageContaining("Start time must be strictly before end time");
        }

        @Test
        @DisplayName("Reject booking where start time is after end time")
        void reject_invertedTimes() {
            CreateBookingRequest req = new CreateBookingRequest(
                    "ROOM-101", "Inverted", "alice@example.com",
                    testDate.atTime(11, 0), testDate.atTime(10, 0),
                    List.of("alice@example.com")
            );

            assertThatThrownBy(() -> bookingService.createBooking(req))
                    .isInstanceOf(InvalidBookingException.class);
        }

        @Test
        @DisplayName("Reject booking with empty attendees list")
        void reject_emptyAttendees() {
            CreateBookingRequest req = new CreateBookingRequest(
                    "ROOM-101", "No attendees", "alice@example.com",
                    testDate.atTime(10, 0), testDate.atTime(11, 0),
                    List.of()
            );

            assertThatThrownBy(() -> bookingService.createBooking(req))
                    .isInstanceOf(InvalidBookingException.class)
                    .hasMessageContaining("Attendees list cannot be empty");
        }

        @Test
        @DisplayName("Updating booking to same time slot does not trigger self-conflict")
        void updateBooking_sameSlot_noSelfConflict() {
            CreateBookingRequest req = new CreateBookingRequest(
                    "ROOM-101", "Original Title", "alice@example.com",
                    testDate.atTime(10, 0), testDate.atTime(11, 0),
                    List.of("alice@example.com")
            );
            BookingResponse created = bookingService.createBooking(req);

            UpdateBookingRequest updateReq = new UpdateBookingRequest();
            updateReq.setTitle("New Title Only");
            updateReq.setStartTime(testDate.atTime(10, 0));
            updateReq.setEndTime(testDate.atTime(11, 0));

            BookingResponse updated = bookingService.updateBooking(created.getId(), updateReq);
            assertThat(updated.getTitle()).isEqualTo("New Title Only");
        }
    }
}
