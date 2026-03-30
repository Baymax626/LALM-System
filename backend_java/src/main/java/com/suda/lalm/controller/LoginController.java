package com.suda.lalm.controller;

import com.suda.lalm.common.ApiResponse;
import com.suda.lalm.dto.LoginRequest;
import com.suda.lalm.entity.User;
import com.suda.lalm.service.UserService;
import org.springframework.web.bind.annotation.*;
import java.util.regex.Pattern;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class LoginController {

    private final UserService userService;

    public LoginController(UserService userService) {
        this.userService = userService;
    }

    @PostMapping("/login")
    public ApiResponse<Map<String, Object>> login(@RequestBody LoginRequest request) {
        String username = request.getUsername() == null ? null : request.getUsername().trim();
        String password = request.getPassword() == null ? null : request.getPassword().trim();
        if (!validUsername(username) || !validPassword(password)) {
            return ApiResponse.error(400, "参数不合法");
        }
        return userService.authenticate(username, password)
                .map(u -> {
                    Map<String, Object> data = new HashMap<>();
                    data.put("token", "mock-token-12345");
                    data.put("username", u.getUsername());
                    data.put("role", "user");
                    return ApiResponse.success("登录成功", data);
                })
                .orElseGet(() -> ApiResponse.error(401, "用户名或密码错误"));
    }
    
    @PostMapping("/register")
    public ApiResponse<Void> register(@RequestBody LoginRequest request) {
        String username = request.getUsername() == null ? null : request.getUsername().trim();
        String password = request.getPassword() == null ? null : request.getPassword().trim();
        if (!validUsername(username) || !validPassword(password)) {
            return ApiResponse.error(400, "参数不合法");
        }
        if (userService.findByUsername(username).isPresent()) {
            return ApiResponse.error(409, "用户名已存在");
        }
        User u = userService.register(username, password);
        return ApiResponse.success("注册成功");
    }

    private boolean validUsername(String username) {
        if (username == null) return false;
        username = username.trim();
        if (username.isEmpty()) return false;
        if (username.length() < 3 || username.length() > 32) return false;
        return Pattern.matches("^[A-Za-z0-9_]+$", username);
    }
    private boolean validPassword(String password) {
        if (password == null) return false;
        password = password.trim();
        if (password.isEmpty()) return false;
        return password.length() >= 6 && password.length() <= 64;
    }
}
