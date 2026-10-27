package com.sdsi.splitter.model;

/**
 * @param paid  total this member paid for the group
 * @param share total of this member's shares across all expenses
 * @param net   paid - share: positive means the member gets money back, negative means they owe
 */
public record MemberBalance(String member, long paid, long share, long net) {
}
