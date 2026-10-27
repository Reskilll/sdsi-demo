package com.sds.ebc.service;

import com.sds.ebc.entity.Opportunity;
import com.sds.ebc.repository.OpportunityRepository;
import org.springframework.stereotype.Service;
import java.time.LocalDateTime;
import java.util.*;

@Service
public class EbcService {

    private final OpportunityRepository repo;
    private static final List<String> STAGES = List.of("Lead generation","RFP received","Go/No-Go","Proposal submitted");
    private static final List<String> SOURCES = List.of("Leader network","Client portal","Referral","Repeat client","Cold outreach","Partner");
    private static final Map<String,Double> SRC_CONVERSION = Map.of("Leader network",0.40,"Client portal",0.21,"Referral",0.50,"Repeat client",0.60,"Cold outreach",0.12,"Partner",0.36);
    private static final Map<String,Double> STAGE_PROB = Map.of("Lead generation",0.10,"RFP received",0.25,"Go/No-Go",0.45,"Proposal submitted",0.70);
    private static final Map<String,Double> REGION_MOD = Map.of("North America",1.0,"Europe",0.95,"Asia-Pacific",1.05,"Middle East",0.9);

    public EbcService(OpportunityRepository repo) { this.repo = repo; }

    public List<Opportunity> getAll() { return repo.findAll(); }
    public Optional<Opportunity> getById(String id) { return repo.findById(id); }
    public List<Opportunity> getOpen() { return repo.findByStatus("open"); }
    public List<Opportunity> getByLeader(String leaderId) { return repo.findByLeaderId(leaderId); }

    public Opportunity create(Opportunity o) {
        if (o.getId() == null) o.setId("OPP-" + (2000 + (int)(Math.random()*9000)));
        o.setCreatedAt(LocalDateTime.now());
        o.setLastUpdate(LocalDateTime.now());
        return repo.save(o);
    }

    public Opportunity advanceStage(String id) {
        return repo.findById(id).map(o -> {
            if ("open".equals(o.getStatus()) && o.getStage() < 3) {
                o.setStage(o.getStage() + 1);
                o.setReached(Math.max(o.getReached(), o.getStage()));
                o.setLastUpdate(LocalDateTime.now());
                return repo.save(o);
            }
            return o;
        }).orElseThrow(() -> new RuntimeException("Opportunity not found: " + id));
    }

    public Opportunity close(String id, String outcome, List<String> reasons, String competitor, String lesson) {
        return repo.findById(id).map(o -> {
            o.setStatus(outcome); o.setCloseDate(LocalDateTime.now());
            o.setCompetitor(competitor); o.setLesson(lesson);
            o.setLastUpdate(LocalDateTime.now());
            return repo.save(o);
        }).orElseThrow(() -> new RuntimeException("Opportunity not found: " + id));
    }

    public Map<String,Object> getDashboard() {
        var all = repo.findAll();
        var won = all.stream().filter(o -> "won".equals(o.getStatus())).toList();
        var lost = all.stream().filter(o -> "lost".equals(o.getStatus())).toList();
        var open = all.stream().filter(o -> "open".equals(o.getStatus())).toList();
        var dropped = all.stream().filter(o -> "dropped".equals(o.getStatus())).toList();
        int dec = won.size() + lost.size();
        double totalWon = won.stream().mapToDouble(Opportunity::getValueLakh).sum();
        double openVal = open.stream().mapToDouble(Opportunity::getValueLakh).sum();
        Map<String,Object> dash = new LinkedHashMap<>();
        dash.put("totalOpportunities", all.size());
        dash.put("wonCount", won.size()); dash.put("lostCount", lost.size());
        dash.put("openCount", open.size()); dash.put("droppedCount", dropped.size());
        dash.put("totalWonValue", totalWon); dash.put("totalOpenValue", openVal);
        dash.put("winRate", dec > 0 ? (double) won.size() / dec : 0);
        dash.put("weightedPipeline", open.stream().mapToDouble(o -> o.getValueLakh() * STAGE_PROB.getOrDefault(STAGES.get(o.getStage()), 0.25)).sum());
        return dash;
    }

    public Map<String,Object> getBidCheck(Map<String,Object> input) {
        String source = (String) input.getOrDefault("source","Referral");
        String region = (String) input.getOrDefault("region","Europe");
        String leaderId = (String) input.getOrDefault("leaderId","L5");
        double value = ((Number) input.getOrDefault("value",150.0)).doubleValue();
        double baseRate = 0.35;
        var all = repo.findAll();
        var closed = all.stream().filter(o -> "won".equals(o.getStatus()) || "lost".equals(o.getStatus())).toList();
        long cTotal = closed.size();
        long cWon = closed.stream().filter(o -> "won".equals(o.getStatus())).count();
        double teamAvg = cTotal > 0 ? (double) cWon / cTotal : 0.45;
        var src = closed.stream().filter(o -> source.equals(o.getSource())).toList();
        double srcRate = src.size() > 0 ? (double) src.stream().filter(o -> "won".equals(o.getStatus())).count() / src.size() : teamAvg;
        var reg = closed.stream().filter(o -> region.equals(o.getBusinessModel())).toList();
        double regRate = reg.size() > 0 ? (double) reg.stream().filter(o -> "won".equals(o.getStatus())).count() / reg.size() : teamAvg;
        double p = (teamAvg * 0.3 + srcRate * 0.35 + regRate * 0.35) * (value < 300 ? 1.05 : 0.9);
        p = Math.max(0.05, Math.min(0.92, p));
        double cost = value * 0.7, price = value, margin = (price - cost) / price;
        Map<String,Object> result = new LinkedHashMap<>();
        result.put("winProbability", Math.round(p * 1000.0) / 1000.0);
        result.put("margin", Math.round(margin * 1000.0) / 1000.0);
        result.put("verdict", p >= 0.5 ? "Bid" : p >= 0.25 ? "Bid with conditions" : "No-bid");
        result.put("teamAverage", Math.round(teamAvg * 1000.0) / 1000.0);
        return result;
    }

    public Map<String,Object> getPipeline() {
        var open = repo.findByStatus("open");
        Map<String,List<Map<String,Object>>> stages = new LinkedHashMap<>();
        for (int i = 0; i < 4; i++) {
            final int s = i; stages.put(STAGES.get(i), open.stream().filter(o -> o.getStage() == s).map(this::toMap).toList());
        }
        Map<String,Object> result = new LinkedHashMap<>();
        result.put("stages", stages);
        result.put("closed", repo.findAll().stream().filter(o -> !"open".equals(o.getStatus())).map(this::toMap).toList());
        return result;
    }

    private Map<String,Object> toMap(Opportunity o) {
        Map<String,Object> m = new LinkedHashMap<>();
        m.put("id",o.getId()); m.put("title",o.getTitle()); m.put("clientId",o.getClientId());
        m.put("valueLakh",o.getValueLakh()); m.put("status",o.getStatus()); m.put("stage",o.getStage());
        m.put("source",o.getSource()); m.put("leaderId",o.getLeaderId());
        m.put("businessModel",o.getBusinessModel()); m.put("closeDate",o.getCloseDate());
        return m;
    }
}
