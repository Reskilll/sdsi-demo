package com.sdsi.booking.web.dto;

import java.util.UUID;

public record CancelSeriesResponse(UUID seriesId, int cancelledCount) {
}
