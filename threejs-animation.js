// Intelligent Virtual Career Advisor - Enhanced Dynamic Background Animation
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { RGBShiftShader } from 'three/addons/shaders/RGBShiftShader.js';
import { gsap } from 'gsap';

let scene, camera, renderer, composer;
let nodes = [], connections = [], particles = [], robots = [];
let mouseX = 0, mouseY = 0;
let lastMouseX = 0, lastMouseY = 0;
let mouseSpeed = 0;
let targetX = 0, targetY = 0;
let windowHalfX = window.innerWidth / 2;
let windowHalfY = window.innerHeight / 2;
let clock, particleSystem, waveObject;
let scrollY = 0;
let lastScrollY = 0;
let scrollSpeed = 0;
let targetScrollY = 0;
let isInitialized = false;
let cursorNode;
let targetRotationX = 0, targetRotationY = 0;

// Update color palette for Three.js animation
const COLORS = {
  primary: 0x6B6054, // Walnut brown
  secondary: 0xA1B0AB, // Ash gray
  accent: 0xC3DAC3, // Tea green
  light: 0xD5ECD4, // Nyanza
  dark: 0x333333,
  highlight: 0x7d7266, // Darker walnut for highlights
};

// Configuration
const TOTAL_NODES = 25;
const CONNECTION_DISTANCE = 2;
const CAMERA_DISTANCE = 8;
const NODE_SIZE_MIN = 0.05;
const NODE_SIZE_MAX = 0.15;

// Track scroll position
window.addEventListener('scroll', () => {
  scrollY = window.scrollY;
});

// Initialize the scene
function init() {
  if (isInitialized) return;
  isInitialized = true;

  clock = new THREE.Clock();
  
  // Create scene
  scene = new THREE.Scene();
  scene.background = new THREE.Color(COLORS.light);
  scene.fog = new THREE.FogExp2(COLORS.light, 0.002);
  
  // Set up renderer
  renderer = new THREE.WebGLRenderer({ 
    canvas: document.getElementById('threeCanvas'),
    antialias: true,
    alpha: true 
  });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1;
  renderer.outputEncoding = THREE.sRGBEncoding;
  
  // Insert canvas to DOM
  document.body.insertBefore(renderer.domElement, document.body.firstChild);
  renderer.domElement.id = 'threeCanvas';
  
  // Add lights
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
  scene.add(ambientLight);
  
  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
  directionalLight.position.set(1, 1, 1);
  scene.add(directionalLight);
  
  // Add point lights in different positions
  addPointLight(COLORS.primary, 3, 2, -2, 1.5);
  addPointLight(COLORS.secondary, -3, -2, -1, 1);
  addPointLight(COLORS.highlight, 0, -1, 2, 1.2);
  
  // Create nodes (career points and opportunities)
  createNodes();
  
  // Create connections between nodes
  createConnections();
  
  // 3D floating icons/symbols (resume, career path, network)
  createFloatingIcons();
  
  // Setup post-processing
  setupPostProcessing();
  
  // Create cursor follower after other elements
  createCursorFollower();
  
  // Event listeners
  document.addEventListener('mousemove', onMouseMove, { passive: true });
  window.addEventListener('resize', onWindowResize);
  window.addEventListener('scroll', onWindowScroll, { passive: true });
  
  // Start animation
  animate();
  
  // Initial animations
  initiateAnimations();
}

function addPointLight(color, x, y, z, intensity) {
  const light = new THREE.PointLight(color, intensity, 10);
  light.position.set(x, y, z);
  scene.add(light);
}

function createNodes() {
  // Create node geometries and materials
  const geometry = new THREE.SphereGeometry(1, 12, 12);
  
  for (let i = 0; i < TOTAL_NODES; i++) {
    // Randomize node appearance
    const size = THREE.MathUtils.randFloat(NODE_SIZE_MIN, NODE_SIZE_MAX);
    const color = new THREE.Color(
      Math.random() > 0.7 ? COLORS.primary : 
      Math.random() > 0.5 ? COLORS.secondary : 
      COLORS.accent
    );
    
    // Create semi-transparent, glowing material
    const material = new THREE.MeshPhysicalMaterial({
      color: color,
      transparent: true,
      opacity: 0.8,
      roughness: 0.2,
      metalness: 0.3,
      emissive: color,
      emissiveIntensity: 0.3
    });
    
    // Create mesh and position it
    const mesh = new THREE.Mesh(geometry, material);
    mesh.scale.set(size, size, size);
    
    // Position within a spherical volume
    const theta = THREE.MathUtils.randFloatSpread(360) * Math.PI / 180;
    const phi = THREE.MathUtils.randFloatSpread(360) * Math.PI / 180;
    const radius = THREE.MathUtils.randFloat(2, 4);
    
    mesh.position.x = radius * Math.sin(theta) * Math.cos(phi);
    mesh.position.y = radius * Math.sin(theta) * Math.sin(phi);
    mesh.position.z = radius * Math.cos(theta);
    
    // Add animation properties
    mesh.userData.phase = Math.random() * Math.PI * 2;
    mesh.userData.speed = THREE.MathUtils.randFloat(0.5, 1.5);
    mesh.userData.pulseSpeed = THREE.MathUtils.randFloat(1, 3);
    mesh.userData.originalScale = size;
    
    // Add to scene and nodes array
    scene.add(mesh);
    nodes.push(mesh);
  }
}

function createConnections() {
  const lineMaterial = new THREE.LineBasicMaterial({ 
    color: COLORS.primary,
    transparent: true,
    opacity: 0.3
  });
  
  // Check for nodes that are close enough to connect
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const distance = nodes[i].position.distanceTo(nodes[j].position);
      
      if (distance < CONNECTION_DISTANCE) {
        const geometry = new THREE.BufferGeometry().setFromPoints([
          nodes[i].position,
          nodes[j].position
        ]);
        
        const line = new THREE.Line(geometry, lineMaterial);
        line.userData = {
          startIndex: i,
          endIndex: j,
          originalOpacity: THREE.MathUtils.randFloat(0.1, 0.4)
        };
        
        scene.add(line);
        connections.push(line);
      }
    }
  }
}

function createFloatingIcons() {
  // Create abstract 3D icons representing career elements
  
  // Resume icon
  const resumeGeometry = new THREE.BoxGeometry(0.5, 0.7, 0.05);
  const resumeMaterial = new THREE.MeshPhysicalMaterial({
    color: new THREE.Color(
      Math.random() > 0.6 ? COLORS.primary : 
      Math.random() > 0.3 ? COLORS.secondary : 
      COLORS.accent
    ),
    transparent: true,
    opacity: 0.9,
    roughness: 0.3,
    metalness: 0.2
  });
  
  const resume = new THREE.Mesh(resumeGeometry, resumeMaterial);
  resume.position.set(2, 1.5, 1);
  resume.userData = {
    rotationSpeed: 0.01,
    floatSpeed: 0.7,
    floatPhase: 0
  };
  scene.add(resume);
  
  // Network node
  const networkGeometry = new THREE.OctahedronGeometry(0.4, 1);
  const networkMaterial = new THREE.MeshPhysicalMaterial({
    color: new THREE.Color(
      Math.random() > 0.6 ? COLORS.primary : 
      Math.random() > 0.3 ? COLORS.secondary : 
      COLORS.accent
    ),
    transparent: true,
    opacity: 0.8,
    roughness: 0.2,
    metalness: 0.4,
    emissive: new THREE.Color(COLORS.highlight),
    emissiveIntensity: 0.3
  });
  
  const network = new THREE.Mesh(networkGeometry, networkMaterial);
  network.position.set(-2, -1, 0.5);
  network.userData = {
    rotationSpeed: 0.02,
    floatSpeed: 0.5,
    floatPhase: Math.PI / 2
  };
  scene.add(network);
  
  // Career path
  const pathPoints = [];
  for (let i = 0; i < 10; i++) {
    const t = i / 9;
    pathPoints.push(
      new THREE.Vector3(
        Math.sin(t * Math.PI * 2) * 0.5,
        t * 0.8 - 0.4,
        Math.cos(t * Math.PI * 2) * 0.5
      )
    );
  }
  
  const pathGeometry = new THREE.BufferGeometry().setFromPoints(pathPoints);
  const pathMaterial = new THREE.LineBasicMaterial({
    color: new THREE.Color(
      Math.random() > 0.6 ? COLORS.primary : 
      Math.random() > 0.3 ? COLORS.secondary : 
      COLORS.accent
    ),
    linewidth: 2
  });
  
  const path = new THREE.Line(pathGeometry, pathMaterial);
  path.position.set(-1.5, 0.5, -1);
  path.userData = {
    rotationSpeed: 0.005,
    floatSpeed: 0.3,
    floatPhase: Math.PI
  };
  scene.add(path);
}

// Setup enhanced post-processing for dramatic visual effects
function setupPostProcessing() {
  composer = new EffectComposer(renderer);
  
  const renderPass = new RenderPass(scene, camera);
  composer.addPass(renderPass);
  
  // Bloom effect for glowing particles
  const bloomPass = new UnrealBloomPass(
    new THREE.Vector2(window.innerWidth, window.innerHeight),
    1.5,  // Strength
    0.4,  // Radius
    0.85  // Threshold
  );
  composer.addPass(bloomPass);
  
  // RGB shift for chromatic effect
  const rgbShiftPass = new ShaderPass(RGBShiftShader);
  rgbShiftPass.uniforms.amount.value = 0.0015;
  rgbShiftPass.uniforms.angle.value = 0;
  composer.addPass(rgbShiftPass);
}

// Enhanced mouse movement handler with speed calculation
function onMouseMove(event) {
  // Store previous position
  lastMouseX = mouseX;
  lastMouseY = mouseY;
  
  // Update mouse position
  mouseX = (event.clientX / window.innerWidth) * 2 - 1;
  mouseY = -(event.clientY / window.innerHeight) * 2 + 1;
  
  // Calculate mouse speed (for effects)
  const dx = mouseX - lastMouseX;
  const dy = mouseY - lastMouseY;
  mouseSpeed = Math.sqrt(dx * dx + dy * dy);
  
  // Update target rotation based on mouse movement
  targetRotationX += dy * 0.5;
  targetRotationY += dx * 0.5;
}

// Window resize handler
function onWindowResize() {
  windowHalfX = window.innerWidth / 2;
  windowHalfY = window.innerHeight / 2;
  
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  
  renderer.setSize(window.innerWidth, window.innerHeight);
  composer.setSize(window.innerWidth, window.innerHeight);
}

// Calculate scroll speed for animations
function updateScrollSpeed() {
  scrollSpeed = Math.abs(scrollY - lastScrollY) * 0.1;
  lastScrollY = scrollY;
  
  scrollSpeed = Math.min(scrollSpeed, 10); // Cap the maximum speed
  return scrollSpeed;
}

// Add a cursor follower node
function createCursorFollower() {
  // Create a glowing sphere that follows the cursor
  const geometry = new THREE.SphereGeometry(0.15, 32, 32);
  const material = new THREE.MeshPhysicalMaterial({
    color: new THREE.Color(
      Math.random() > 0.6 ? COLORS.primary : 
      Math.random() > 0.3 ? COLORS.secondary : 
      COLORS.accent
    ),
    transparent: true,
    opacity: 0.8,
    roughness: 0.1,
    metalness: 0.6,
    emissive: new THREE.Color(COLORS.highlight),
    emissiveIntensity: 0.5
  });
  
  cursorNode = new THREE.Mesh(geometry, material);
  cursorNode.position.set(0, 0, 3); // Place in front of camera
  scene.add(cursorNode);
  
  // Add a trail effect
  const trailGeometry = new THREE.BufferGeometry();
  const trailPositions = new Float32Array(30 * 3); // 30 points, 3 coordinates each
  
  // Initialize trail points
  for (let i = 0; i < 30; i++) {
    trailPositions[i * 3] = 0;
    trailPositions[i * 3 + 1] = 0;
    trailPositions[i * 3 + 2] = 3;
  }
  
  trailGeometry.setAttribute('position', new THREE.BufferAttribute(trailPositions, 3));
  
  const trailMaterial = new THREE.LineBasicMaterial({
    color: new THREE.Color(
      Math.random() > 0.6 ? COLORS.primary : 
      Math.random() > 0.3 ? COLORS.secondary : 
      COLORS.accent
    ),
    transparent: true,
    opacity: 0.5,
    linewidth: 1
  });
  
  const trail = new THREE.Line(trailGeometry, trailMaterial);
  cursorNode.trail = trail;
  cursorNode.trailPositions = trailPositions;
  cursorNode.trailUpdateCounter = 0;
  scene.add(trail);
}

// Add more responsive camera and scene reactions to scroll
function onWindowScroll() {
  targetScrollY = window.scrollY;
  
  // Calculate scroll percentage (0 to 1)
  const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
  const scrollPercentage = targetScrollY / scrollHeight;
  
  // Tilt the camera based on scroll position
  const maxTilt = 0.3; // Maximum camera tilt in radians
  targetRotationX = (scrollPercentage - 0.5) * maxTilt;
  
  // Scale animation intensity based on scroll speed
  const scrollDelta = Math.abs(targetScrollY - lastScrollY);
  const normalizedScrollSpeed = Math.min(scrollDelta / 50, 1);
  
  // Apply effects based on scroll speed
  if (normalizedScrollSpeed > 0.3) {
    // Increase bloom intensity temporarily
    if (composer.passes[1].strength < 2.5) {
      composer.passes[1].strength += normalizedScrollSpeed * 0.2;
    }
    
    // Create a wave effect through nodes
    nodes.forEach((node, index) => {
      gsap.to(node.scale, {
        x: node.userData.originalScale * (1.2 + normalizedScrollSpeed * 0.3),
        y: node.userData.originalScale * (1.2 + normalizedScrollSpeed * 0.3),
        z: node.userData.originalScale * (1.2 + normalizedScrollSpeed * 0.3),
        duration: 0.3,
        ease: "power2.out",
        delay: index * 0.01,
        yoyo: true,
        repeat: 1
      });
    });
  } else {
    // Gradually restore bloom to normal
    if (composer.passes[1].strength > 1.5) {
      composer.passes[1].strength -= 0.05;
    }
  }
  
  lastScrollY = targetScrollY;
}

// Updated animation loop with enhanced cursor following
function animate() {
  requestAnimationFrame(animate);
  
  // Get elapsed time for animations
  const time = clock.getElapsedTime();
  
  // Update cursor follower if it exists
  if (cursorNode) {
    // Calculate target position in 3D space
    const targetX = mouseX * 3;
    const targetY = mouseY * 2;
    
    // Smooth follow with easing
    cursorNode.position.x += (targetX - cursorNode.position.x) * 0.1;
    cursorNode.position.y += (targetY - cursorNode.position.y) * 0.1;
    
    // Pulse size based on mouse speed
    const scale = 0.15 + mouseSpeed * 1.5;
    cursorNode.scale.set(scale, scale, scale);
    
    // Update cursor glow intensity based on mouse speed
    cursorNode.material.emissiveIntensity = 0.5 + mouseSpeed * 2;
    
    // Update trail positions
    if (cursorNode.trailUpdateCounter % 2 === 0) { // Update every other frame for performance
      // Shift all positions down by one
      for (let i = cursorNode.trailPositions.length / 3 - 1; i > 0; i--) {
        cursorNode.trailPositions[i * 3] = cursorNode.trailPositions[(i - 1) * 3];
        cursorNode.trailPositions[i * 3 + 1] = cursorNode.trailPositions[(i - 1) * 3 + 1];
        cursorNode.trailPositions[i * 3 + 2] = cursorNode.trailPositions[(i - 1) * 3 + 2];
      }
      
      // Set first position to current cursor position
      cursorNode.trailPositions[0] = cursorNode.position.x;
      cursorNode.trailPositions[1] = cursorNode.position.y;
      cursorNode.trailPositions[2] = cursorNode.position.z;
      
      // Update the buffer attribute
      cursorNode.trail.geometry.attributes.position.needsUpdate = true;
    }
    cursorNode.trailUpdateCounter++;
    
    // Fade trail opacity based on mouse speed
    cursorNode.trail.material.opacity = Math.min(0.5, mouseSpeed * 3);
  }
  
  // Rotate and animate nodes with interaction with cursor
  nodes.forEach((node, index) => {
    // Pulsing size effect
    const pulse = Math.sin(time * node.userData.pulseSpeed + node.userData.phase) * 0.1 + 1;
    const size = node.userData.originalScale * pulse;
    node.scale.set(size, size, size);
    
    // Gentle rotation
    node.rotation.x += 0.003 * node.userData.speed;
    node.rotation.y += 0.005 * node.userData.speed;
    
    // Subtle position animation
    const posNoise = Math.sin(time * 0.5 + index) * 0.02;
    node.position.x += posNoise * Math.sin(time * 0.2 + index);
    node.position.y += posNoise * Math.cos(time * 0.3 + index);
    node.position.z += posNoise * Math.sin(time * 0.4 + index * 2);
    
    // Nodes react to cursor proximity
    if (cursorNode) {
      const distance = node.position.distanceTo(cursorNode.position);
      if (distance < 1.5) {
        // Apply gentle force away from cursor
        const repelFactor = (1.5 - distance) * 0.01;
        const directionX = node.position.x - cursorNode.position.x;
        const directionY = node.position.y - cursorNode.position.y;
        const directionZ = node.position.z - cursorNode.position.z;
        
        // Normalize and apply force
        const length = Math.sqrt(directionX * directionX + directionY * directionY + directionZ * directionZ);
        if (length > 0) {
          node.position.x += (directionX / length) * repelFactor;
          node.position.y += (directionY / length) * repelFactor;
          node.position.z += (directionZ / length) * repelFactor;
        }
        
        // Increase glow when near cursor
        node.material.emissiveIntensity = 0.3 + (1.5 - distance) * 0.5;
      } else if (node.material.emissiveIntensity > 0.3) {
        // Fade back to normal glow
        node.material.emissiveIntensity -= 0.02;
      }
    }
  });
  
  // Smooth camera rotation
  camera.rotation.x += (targetRotationX - camera.rotation.x) * 0.05;
  camera.rotation.y += (targetRotationY - camera.rotation.y) * 0.05;
  
  // Animate connections
  connections.forEach(connection => {
    // Update line positions based on connected nodes
    const startNode = nodes[connection.userData.startIndex];
    const endNode = nodes[connection.userData.endIndex];
    
    const points = connection.geometry.attributes.position;
    points.setXYZ(0, startNode.position.x, startNode.position.y, startNode.position.z);
    points.setXYZ(1, endNode.position.x, endNode.position.y, endNode.position.z);
    points.needsUpdate = true;
    
    // Pulse opacity
    const opacityPulse = Math.sin(time + connection.userData.startIndex) * 0.15 + 0.85;
    connection.material.opacity = connection.userData.originalOpacity * opacityPulse;
    
    // Connections react to cursor proximity
    if (cursorNode) {
      // Check if cursor is near this connection
      const midX = (startNode.position.x + endNode.position.x) * 0.5;
      const midY = (startNode.position.y + endNode.position.y) * 0.5;
      const midZ = (startNode.position.z + endNode.position.z) * 0.5;
      
      const distance = Math.sqrt(
        Math.pow(midX - cursorNode.position.x, 2) +
        Math.pow(midY - cursorNode.position.y, 2) +
        Math.pow(midZ - cursorNode.position.z, 2)
      );
      
      if (distance < 1.0) {
        // Increase opacity and glow when cursor is near
        connection.material.opacity = Math.min(0.8, connection.material.opacity + 0.1);
        connection.material.color.setHex(COLORS.highlight);
      } else if (connection.material.color.getHex() === COLORS.highlight) {
        // Fade back to original color
        connection.material.color.setHex(COLORS.primary);
      }
    }
  });
  
  // Find and animate any floating icons
  scene.traverse(object => {
    if (object.userData.floatSpeed !== undefined) {
      // Floating motion
      object.position.y += Math.sin(time * object.userData.floatSpeed + object.userData.floatPhase) * 0.005;
      
      // Rotation
      object.rotation.x += object.userData.rotationSpeed * 0.5;
      object.rotation.y += object.userData.rotationSpeed;
      object.rotation.z += object.userData.rotationSpeed * 0.3;
      
      // React to cursor
      if (cursorNode) {
        const distance = object.position.distanceTo(cursorNode.position);
        if (distance < 1.0) {
          // Look at cursor
          object.lookAt(cursorNode.position);
          
          // Scale up slightly
          const scale = 1.0 + (1.0 - distance) * 0.3;
          object.scale.set(scale, scale, scale);
          
          // Increase emissive intensity if available
          if (object.material.emissiveIntensity !== undefined) {
            object.material.emissiveIntensity = 0.3 + (1.0 - distance) * 0.7;
          }
        } else if (object.scale.x > 1.0) {
          // Scale back down
          object.scale.x -= 0.01;
          object.scale.y -= 0.01;
          object.scale.z -= 0.01;
          
          if (object.material.emissiveIntensity !== undefined && object.material.emissiveIntensity > 0.3) {
            object.material.emissiveIntensity -= 0.02;
          }
        }
      }
    }
  });
  
  // Camera movement based on mouse position with added physics
  camera.position.x += (mouseX * 1.5 - camera.position.x) * 0.03;
  camera.position.y += (mouseY * 1.0 - camera.position.y) * 0.03;
  camera.lookAt(scene.position);
  
  // Render the scene
  composer.render();
}

// Initial animations when the page loads
function initiateAnimations() {
  // Rotate the energy wave
  gsap.to(waveObject.rotation, {
    z: Math.PI * 2,
    duration: 20,
    repeat: -1,
    ease: "none"
  });
  
  // Pulse the energy wave
  gsap.to(waveObject.scale, {
    x: 1.2,
    y: 1.2,
    z: 1.2,
    duration: 2,
    repeat: -1,
    yoyo: true,
    ease: "sine.inOut"
  });
  
  // Pulse the antenna tip
  const antennaTip = robotHead.children[2].children[0];
  gsap.to(antennaTip.scale, {
    x: 1.5,
    y: 1.5,
    z: 1.5,
    duration: 0.5,
    repeat: -1,
    yoyo: true,
    ease: "sine.inOut"
  });
  
  // Subtle float animation for robot parts
  gsap.to(robotHead.position, {
    y: '+=10',
    duration: 3,
    repeat: -1,
    yoyo: true,
    ease: "sine.inOut"
  });
  
  gsap.to(robotBody.position, {
    y: '+=8',
    duration: 2.5,
    repeat: -1,
    yoyo: true,
    ease: "sine.inOut",
    delay: 0.5
  });
}

// Start the animation
window.addEventListener('load', init);

export { init }; 