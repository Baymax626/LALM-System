package com.suda.lalm.controller;

import com.suda.lalm.common.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class HealthController {
    @GetMapping("/ping")
    public ApiResponse<String> ping() {
        return ApiResponse.success("ok", "ok");
    }
}
