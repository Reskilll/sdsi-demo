package com.sds.ebc.controller;

import com.sds.ebc.entity.Opportunity;
import com.sds.ebc.service.EbcService;
import org.springframework.web.bind.annotation.*;
import java.util.*;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "http://localhost:5173")
public class EbcController {

    private final EbcService service;
    public EbcController(EbcService service) { this.service = service; }

    @GetMapping("/dashboard")
    public Map<String,Object> dashboard() { return service.getDashboard(); }

    @GetMapping("/opportunities")
    public List<Opportunity> getAll() { return service.getAll(); }

    @GetMapping("/opportunities/{id}")
    public Optional<Opportunity> getOne(@PathVariable String id) { return service.getById(id); }

    @GetMapping("/opportunities/open")
    public List<Opportunity> getOpen() { return service.getOpen(); }

    @PostMapping("/opportunities")
    public Opportunity create(@RequestBody Opportunity o) { return service.create(o); }

    @PostMapping("/opportunities/{id}/advance")
    public Opportunity advance(@PathVariable String id) { return service.advanceStage(id); }

    @PostMapping("/opportunities/{id}/close")
    public Opportunity close(@PathVariable String id, @RequestBody Map<String,Object> body) {
        return service.close(id,
            (String) body.get("outcome"),
            (List<String>) body.getOrDefault("reasons", List.of()),
            (String) body.getOrDefault("competitor", ""),
            (String) body.getOrDefault("lesson", "")
        );
    }

    @PostMapping("/bid-check")
    public Map<String,Object> bidCheck(@RequestBody Map<String,Object> input) {
        return service.getBidCheck(input);
    }

    @GetMapping("/pipeline")
    public Map<String,Object> pipeline() { return service.getPipeline(); }

    @GetMapping("/health")
    public Map<String,String> health() { return Map.of("status","UP","app","EBC Backend"); }

    @GetMapping("/stats/sources")
    public Map<String,Object> sourceStats() {
        var all = service.getAll();
        Map<String,Object> result = new LinkedHashMap<>();
        for (String src : List.of("Leader network","Client portal","Referral","Repeat client","Cold outreach","Partner")) {
            var s = all.stream().filter(o -> src.equals(o.getSource())).toList();
            int w = (int) s.stream().filter(o -> "won".equals(o.getStatus())).count();
            Map<String,Object> m = new LinkedHashMap<>();
            m.put("total", s.size()); m.put("won", w);
            m.put("rate", s.size() > 0 ? Math.round((double)w / s.size() * 1000.0) / 1000.0 : 0);
            result.put(src, m);
        }
        return result;
    }
}
