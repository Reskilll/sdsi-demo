-- Schema for the H2 database (file-backed locally, in-memory in tests).
-- All times are office wall-clock time (no timezone conversion), see README.

create table room (
    id       varchar(40)  not null primary key,
    name     varchar(80)  not null unique,
    capacity integer      not null,
    floor    integer,
    location varchar(120),
    active   boolean      not null default true,
    constraint ck_room_capacity check (capacity > 0)
);

create table room_amenity (
    room_id varchar(40) not null,
    amenity varchar(40) not null,
    primary key (room_id, amenity),
    constraint fk_room_amenity_room foreign key (room_id) references room (id) on delete cascade
);

create table booking_series (
    id             uuid         not null primary key,
    room_id        varchar(40)  not null,
    organiser      varchar(120) not null,
    organiser_email varchar(160),
    title          varchar(160) not null,
    description    varchar(1000),
    start_time     time         not null,
    end_time       time         not null,
    starts_on      date         not null,
    weeks          integer      not null,
    days_of_week   varchar(100) not null,
    attendee_count integer      not null,
    created_at     timestamp with time zone not null,
    constraint fk_series_room foreign key (room_id) references room (id),
    constraint ck_series_weeks check (weeks between 1 and 52)
);

create table series_attendee (
    series_id uuid         not null,
    email     varchar(160) not null,
    primary key (series_id, email),
    constraint fk_series_attendee_series foreign key (series_id) references booking_series (id) on delete cascade
);

create table booking (
    id             uuid         not null primary key,
    room_id        varchar(40)  not null,
    series_id      uuid,
    occurrence_index integer,
    organiser      varchar(120) not null,
    organiser_email varchar(160),
    title          varchar(160) not null,
    description    varchar(1000),
    start_at       timestamp    not null,
    end_at         timestamp    not null,
    attendee_count integer      not null,
    status         varchar(16)  not null,
    created_at     timestamp with time zone not null,
    updated_at     timestamp with time zone not null,
    version        bigint       not null default 0,
    constraint fk_booking_room foreign key (room_id) references room (id),
    constraint fk_booking_series foreign key (series_id) references booking_series (id),
    constraint ck_booking_interval check (end_at > start_at),
    constraint ck_booking_attendees check (attendee_count > 0)
);

create index idx_booking_room_start on booking (room_id, start_at, end_at);
create index idx_booking_series on booking (series_id);
create index idx_booking_organiser on booking (organiser);

create table booking_attendee (
    booking_id uuid         not null,
    email      varchar(160) not null,
    primary key (booking_id, email),
    constraint fk_booking_attendee_booking foreign key (booking_id) references booking (id) on delete cascade
);
