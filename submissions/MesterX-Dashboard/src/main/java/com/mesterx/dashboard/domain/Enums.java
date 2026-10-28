package com.mesterx.dashboard.domain;

public final class Enums {
    private Enums() {}

    public enum Role { ADMIN, PROJECT_MANAGER, DEVELOPER }
    public enum UserStatus { ACTIVE, DISABLED }
    public enum Tier { WORKER, EXPERT }
    public enum Scope { GLOBAL, PROJECT, USER }
    public enum ProjectRole { MANAGER, MEMBER }
    public enum Outcome { SUCCESS, ERROR, WORKER_ONLY }
    public enum StatusCategory { TODO, IN_PROGRESS, DONE }
    public enum BudgetState { OK, WARNING, EXCEEDED, NONE }
}
