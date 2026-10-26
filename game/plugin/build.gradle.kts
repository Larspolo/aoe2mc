// The Paper plugin of the game program (#435). game/run.py builds it with the wrapper (Java 25).
plugins {
    java
}

repositories {
    maven("https://repo.papermc.io/repository/maven-public/")
    mavenCentral()
}

dependencies {
    compileOnly("io.papermc.paper:paper-api:26.3.build.223-stable")
}

tasks.withType<JavaCompile> {
    options.release.set(25)
    options.encoding = "UTF-8"
}

tasks.jar {
    archiveFileName.set("aoe2mc-plugin.jar")
}
