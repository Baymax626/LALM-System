package com.suda.lalm.service;

import com.suda.lalm.entity.User;
import com.suda.lalm.repository.UserRepository;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.util.HexFormat;
import java.util.Optional;

@Service
public class UserService {

    private final UserRepository userRepository;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    public Optional<User> findByUsername(String username) {
        return userRepository.findByUsername(username);
    }

    public Optional<User> authenticate(String username, String passwordPlain) {
        return userRepository.findByUsername(username)
                .filter(u -> u.getPasswordHash().equals(hash(passwordPlain)));
    }

    public User register(String username, String passwordPlain) {
        User user = new User();
        user.setUsername(username);
        user.setPasswordHash(hash(passwordPlain));
        user.setCreatedAt(LocalDateTime.now());
        return userRepository.save(user);
    }

    private String hash(String s) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(s.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
