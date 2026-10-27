package com.sds.ebc.repository;

import com.sds.ebc.entity.Opportunity;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface OpportunityRepository extends JpaRepository<Opportunity, String> {
    List<Opportunity> findByStatus(String status);
    List<Opportunity> findByLeaderId(String leaderId);
    List<Opportunity> findByStatusNot(String status);
    List<Opportunity> findByClientId(Long clientId);
}
