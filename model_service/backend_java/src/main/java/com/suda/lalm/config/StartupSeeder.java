package com.suda.lalm.config;

import com.suda.lalm.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class StartupSeeder implements CommandLineRunner {
    private final UserService userService;

    @Override
    public void run(String... args) {
        userService.findByUsername("admin")
                .orElseGet(() -> userService.register("admin", "123456"));
    }
}
