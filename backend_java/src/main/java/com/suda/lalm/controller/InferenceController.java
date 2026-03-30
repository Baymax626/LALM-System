package com.suda.lalm.controller;

import com.suda.lalm.common.ApiResponse;
import com.suda.lalm.entity.InferenceRecord;
import com.suda.lalm.entity.User;
import com.suda.lalm.service.InferenceRecordService;
import com.suda.lalm.service.ModelService;
import com.suda.lalm.service.UserService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
@Slf4j
public class InferenceController {

    private final ModelService modelService;
    private final InferenceRecordService recordService;
    private final UserService userService;

    @PostMapping("/inference")
    public ResponseEntity<ApiResponse<Map<String, Object>>> inference(
            @RequestParam("prompt") String prompt,
            @RequestParam(value = "file", required = false) MultipartFile file,
            @RequestParam(value = "stage", defaultValue = "0") int stage,
            @RequestParam(value = "context", defaultValue = "") String context,
            @RequestParam(value = "username", defaultValue = "admin") String username) {
        
        log.info("Inference request - Stage: {}, Prompt: {}", stage, prompt);
        
        Map<String, Object> result = modelService.callModel(prompt, file, stage, context);
        
        // 仅在最终阶段保存记录
        if (stage == 4 || stage == 0) {
            User user = userService.findByUsername(username).orElseGet(() -> userService.register(username, "123456"));
            InferenceRecord record = recordService.saveRecord(user, prompt, (String)result.get("asr_text"), result);
            result.put("recordId", record.getId());
        }
        
        return ResponseEntity.ok(ApiResponse.success(result));
    }

    @GetMapping("/history")
    public ResponseEntity<ApiResponse<List<InferenceRecord>>> getHistory(@RequestParam("username") String username) {
        User user = userService.findByUsername(username).orElseThrow(() -> new RuntimeException("User not found"));
        List<InferenceRecord> history = recordService.getUserHistory(user);
        return ResponseEntity.ok(ApiResponse.success(history));
    }

    @PostMapping("/feedback/submit")
    public ResponseEntity<ApiResponse<Void>> submitFeedback(@RequestBody Map<String, Object> body) {
        Long recordId = Long.valueOf(body.get("recordId").toString());
        Integer rating = Integer.valueOf(body.get("rating").toString());
        String comment = (String) body.get("comment");
        
        recordService.saveFeedback(recordId, rating, comment);
        return ResponseEntity.ok(ApiResponse.success("Feedback submitted"));
    }
}
