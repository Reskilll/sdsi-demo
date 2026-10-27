package com.sdsi.splitter.model;

/** "{@code from} pays {@code to} ₹amount". */
public record Settlement(String from, String to, long amountPaise) {
}
