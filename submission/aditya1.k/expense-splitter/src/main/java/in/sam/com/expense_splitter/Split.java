package in.sam.com.expense_splitter;

import java.math.BigDecimal;

public class Split {
    private String member;
    private BigDecimal value;

    public Split() {
    }

    public Split(String member, BigDecimal value) {
        this.member = member;
        this.value = value;
    }

    public String getMember() {
        return member;
    }

    public void setMember(String member) {
        this.member = member;
    }

    public BigDecimal getValue() {
        return value;
    }

    public void setValue(BigDecimal value) {
        this.value = value;
    }
}
