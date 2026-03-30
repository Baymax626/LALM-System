package com.suda.lalm.controller;

import com.suda.lalm.common.ApiResponse;
import com.suda.lalm.service.ModelService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
@Slf4j
public class InferenceController {

    private final ModelService modelService;

    @PostMapping("/inference")
    public ResponseEntity<ApiResponse<Map<String, Object>>> inference(
            @RequestParam("prompt") String prompt,
            @RequestParam(value = "file", required = false) MultipartFile file) {
        
        // 接收来自前端的 Prompt 和录音文件（可选），交由服务层转发到 Python
        log.info("Received inference request. Prompt length: {}", prompt.length());
        
        Map<String, Object> result = modelService.callModel(prompt, file);
        // 将 Python 返回的 JSON 结果包装为统一的 ApiResponse
        return ResponseEntity.ok(ApiResponse.success(result));
    }
}
