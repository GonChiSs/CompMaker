from __future__ import annotations

import random
import re
from dataclasses import dataclass, field


class OptimizationTarget:
    PHYSICAL_DPS = "PHYSICAL_DPS"
    MAGIC_DPS = "MAGIC_DPS"
    HYBRID_DPS = "HYBRID_DPS"
    TANK_HP = "TANK_HP"
    TANK_ARMOR = "TANK_ARMOR"
    TANK_MR = "TANK_MR"
    UTILITY = "UTILITY"
    GOLD_EFFICIENCY = "GOLD_EFFICIENCY"
    LETHALITY = "LETHALITY"
    LIFESTEAL_DPS = "LIFESTEAL_DPS"


TARGET_LABELS = {
    OptimizationTarget.PHYSICAL_DPS: "DPS fisico maximo",
    OptimizationTarget.MAGIC_DPS: "DPS magico maximo",
    OptimizationTarget.HYBRID_DPS: "DPS hibrido",
    OptimizationTarget.TANK_HP: "Tanque mixto",
    OptimizationTarget.TANK_ARMOR: "Tanque vs fisico",
    OptimizationTarget.TANK_MR: "Tanque vs magia",
    OptimizationTarget.UTILITY: "Utilidad maxima",
    OptimizationTarget.GOLD_EFFICIENCY: "Eficiencia de oro",
    OptimizationTarget.LETHALITY: "Burst letalidad",
    OptimizationTarget.LIFESTEAL_DPS: "DPS con sustain",
}

ROLE_DEFAULT_TARGET = {
    "top": OptimizationTarget.TANK_HP,
    "jungle": OptimizationTarget.PHYSICAL_DPS,
    "middle": OptimizationTarget.MAGIC_DPS,
    "bottom": OptimizationTarget.PHYSICAL_DPS,
    "support": OptimizationTarget.UTILITY,
}

GA_POPULATION = 120
GA_GENERATIONS = 60
GA_MUTATION_RATE = 0.18
GA_ELITE_RATIO = 0.12
BUILD_SIZE = 6

ITEM_IDS = {
    "Rabadons": 3089,
    "InfinityEdge": 3031,
    "Navori": 6675,
    "Kraken": 6672,
    "Rageblade": 3124,
    "Shieldbow": 6673,
    "Eclipse": 6692,
    "Hullbreaker": 3153,
    "BlackCleaver": 3071,
    "DeathsDance": 6333,
    "SteraksGage": 3053,
    "Sunfire": 3068,
    "Riftmaker": 4633,
    "LiandrysAnguish": 6653,
    "Malignance": 4628,
    "Shojin": 3161,
    "Archangels": 4636,
    "Moonflair": 4629,
    "GuardianAngel": 3026,
    "Bloodthirster": 3072,
    "WitsEnd": 3091,
    "Terminus": 6701,
    "Nashors": 3115,
}

MUTUALLY_EXCLUSIVE_GROUPS = [
    {ITEM_IDS["Hullbreaker"], ITEM_IDS["Sunfire"]},
]

UNIQUE_PASSIVE_RE = re.compile(r"[Uu]nique\s*[\u2013\-:]\s*([A-Za-z' ]+):")


@dataclass
class GAResult:
    item_ids: list[int]
    fitness: float
    target: str
    stats: dict[str, float]
    breakdown: dict[str, float]
    generation: int
    generations_run: int
    total_gold: int


@dataclass
class ChampionItemProfile:
    abilities_can_crit: bool = False
    on_hit_value_mult: float = 1.0
    crit_value_mult: float = 1.0
    ability_rotations_per_fight: float = 3.5
    resource_dependency: float = 0.0
    item_synergies: dict[int, float] = field(default_factory=dict)
    item_penalties: dict[int, float] = field(default_factory=dict)


DEFAULT_PROFILE = ChampionItemProfile()

CHAMPION_PROFILES: dict[str, ChampionItemProfile] = {
    "Kog'Maw": ChampionItemProfile(
        on_hit_value_mult=1.8,
        crit_value_mult=0.6,
        item_synergies={
            ITEM_IDS["Rageblade"]: 1.30,
            ITEM_IDS["WitsEnd"]: 1.20,
            ITEM_IDS["Terminus"]: 1.15,
        },
        item_penalties={ITEM_IDS["InfinityEdge"]: 0.60},
    ),
    "Twitch": ChampionItemProfile(
        on_hit_value_mult=1.6,
        crit_value_mult=1.1,
        item_synergies={
            ITEM_IDS["Kraken"]: 1.25,
            ITEM_IDS["Rageblade"]: 1.20,
        },
    ),
    "Vayne": ChampionItemProfile(
        on_hit_value_mult=1.5,
        crit_value_mult=1.2,
        item_synergies={
            ITEM_IDS["Kraken"]: 1.20,
            ITEM_IDS["Terminus"]: 1.15,
        },
    ),
    "Kayle": ChampionItemProfile(
        on_hit_value_mult=1.4,
        ability_rotations_per_fight=2.0,
        item_synergies={
            ITEM_IDS["Nashors"]: 1.30,
            ITEM_IDS["Rageblade"]: 1.20,
        },
    ),
    "Yasuo": ChampionItemProfile(
        abilities_can_crit=True,
        crit_value_mult=1.5,
        item_synergies={
            ITEM_IDS["InfinityEdge"]: 1.40,
            ITEM_IDS["Navori"]: 1.30,
        },
    ),
    "Yone": ChampionItemProfile(
        abilities_can_crit=True,
        crit_value_mult=1.45,
        item_synergies={
            ITEM_IDS["InfinityEdge"]: 1.35,
            ITEM_IDS["Navori"]: 1.25,
        },
    ),
    "Jhin": ChampionItemProfile(
        abilities_can_crit=True,
        crit_value_mult=1.6,
        on_hit_value_mult=0.7,
        item_synergies={
            ITEM_IDS["InfinityEdge"]: 1.40,
            ITEM_IDS["Navori"]: 1.20,
        },
        item_penalties={ITEM_IDS["Rageblade"]: 0.30},
    ),
    "Kai'Sa": ChampionItemProfile(
        abilities_can_crit=True,
        crit_value_mult=1.3,
        on_hit_value_mult=1.2,
        item_synergies={
            ITEM_IDS["Navori"]: 1.25,
            ITEM_IDS["Kraken"]: 1.20,
        },
    ),
    "Tryndamere": ChampionItemProfile(
        abilities_can_crit=True,
        crit_value_mult=1.4,
        resource_dependency=0.1,
        item_synergies={
            ITEM_IDS["Bloodthirster"]: 1.30,
            ITEM_IDS["InfinityEdge"]: 1.25,
        },
    ),
    "Cassiopeia": ChampionItemProfile(
        on_hit_value_mult=0.5,
        ability_rotations_per_fight=5.0,
        resource_dependency=0.4,
        item_synergies={
            ITEM_IDS["LiandrysAnguish"]: 1.40,
            ITEM_IDS["Riftmaker"]: 1.30,
            ITEM_IDS["Shojin"]: 1.20,
        },
    ),
    "Vladimir": ChampionItemProfile(
        ability_rotations_per_fight=3.0,
        item_synergies={
            ITEM_IDS["Riftmaker"]: 1.35,
            ITEM_IDS["Shieldbow"]: 1.10,
        },
    ),
    "Karthus": ChampionItemProfile(
        ability_rotations_per_fight=4.0,
        resource_dependency=0.3,
        item_synergies={
            ITEM_IDS["LiandrysAnguish"]: 1.30,
            ITEM_IDS["Shojin"]: 1.20,
        },
    ),
    "Zed": ChampionItemProfile(
        ability_rotations_per_fight=1.0,
        item_synergies={
            ITEM_IDS["Eclipse"]: 1.35,
            ITEM_IDS["DeathsDance"]: 1.20,
        },
        item_penalties={ITEM_IDS["Rageblade"]: 0.20},
    ),
    "Talon": ChampionItemProfile(
        ability_rotations_per_fight=1.0,
        item_synergies={
            ITEM_IDS["Eclipse"]: 1.30,
            ITEM_IDS["DeathsDance"]: 1.15,
        },
    ),
    "Katarina": ChampionItemProfile(
        abilities_can_crit=True,
        crit_value_mult=1.1,
        ability_rotations_per_fight=4.0,
        resource_dependency=0.3,
        item_synergies={
            ITEM_IDS["Riftmaker"]: 1.25,
            ITEM_IDS["Shojin"]: 1.20,
        },
    ),
    "Malphite": ChampionItemProfile(
        ability_rotations_per_fight=1.0,
        item_synergies={
            ITEM_IDS["Riftmaker"]: 1.20,
            ITEM_IDS["Sunfire"]: 1.15,
        },
    ),
    "Amumu": ChampionItemProfile(
        ability_rotations_per_fight=1.0,
        item_synergies={
            ITEM_IDS["Riftmaker"]: 1.25,
            ITEM_IDS["LiandrysAnguish"]: 1.20,
        },
    ),
    "Darius": ChampionItemProfile(
        ability_rotations_per_fight=2.0,
        item_synergies={
            ITEM_IDS["BlackCleaver"]: 1.30,
            ITEM_IDS["SteraksGage"]: 1.20,
            ITEM_IDS["DeathsDance"]: 1.15,
        },
    ),
    "Garen": ChampionItemProfile(
        ability_rotations_per_fight=2.0,
        item_synergies={
            ITEM_IDS["BlackCleaver"]: 1.25,
            ITEM_IDS["SteraksGage"]: 1.20,
        },
    ),
    "Lulu": ChampionItemProfile(resource_dependency=0.5, ability_rotations_per_fight=4.0),
    "Janna": ChampionItemProfile(resource_dependency=0.5, ability_rotations_per_fight=3.0),
    "Syndra": ChampionItemProfile(
        ability_rotations_per_fight=2.0,
        resource_dependency=0.4,
        item_synergies={
            ITEM_IDS["Malignance"]: 1.30,
            ITEM_IDS["Shojin"]: 1.15,
        },
    ),
    "Orianna": ChampionItemProfile(
        ability_rotations_per_fight=2.5,
        resource_dependency=0.3,
        item_synergies={
            ITEM_IDS["Shojin"]: 1.20,
            ITEM_IDS["Malignance"]: 1.20,
        },
    ),
    "Jinx": ChampionItemProfile(
        on_hit_value_mult=0.6,
        crit_value_mult=1.3,
        item_synergies={
            ITEM_IDS["Kraken"]: 1.20,
            ITEM_IDS["InfinityEdge"]: 1.25,
        },
        item_penalties={ITEM_IDS["Rageblade"]: 0.40},
    ),
    "Ezreal": ChampionItemProfile(
        on_hit_value_mult=1.3,
        crit_value_mult=0.9,
        item_synergies={ITEM_IDS["Shojin"]: 1.20},
    ),
}

ACTIVE_ITEM_SYNERGIES = {
    "Cassiopeia": {ITEM_IDS["Riftmaker"]: 1.10},
    "Karthus": {ITEM_IDS["Riftmaker"]: 1.10},
    "Ryze": {ITEM_IDS["Riftmaker"]: 1.05},
}


def get_champion_profile(champion_name: str) -> ChampionItemProfile:
    base = CHAMPION_PROFILES.get(champion_name, DEFAULT_PROFILE)
    extra = ACTIVE_ITEM_SYNERGIES.get(champion_name, {})
    if not extra:
        return base
    merged_synergies = dict(base.item_synergies)
    for item_id, mult in extra.items():
        merged_synergies[item_id] = merged_synergies.get(item_id, 1.0) * mult
    return ChampionItemProfile(
        abilities_can_crit=base.abilities_can_crit,
        on_hit_value_mult=base.on_hit_value_mult,
        crit_value_mult=base.crit_value_mult,
        ability_rotations_per_fight=base.ability_rotations_per_fight,
        resource_dependency=base.resource_dependency,
        item_synergies=merged_synergies,
        item_penalties=dict(base.item_penalties),
    )


class GeneticBuildOptimizer:
    def __init__(
        self,
        items: dict[int, dict],
        champion_stats: dict,
        target: str,
        champion_level: int = 18,
        progress_callback=None,
        constraints: dict | None = None,
        role: str = "middle",
        champion_name: str = "",
    ):
        self.items = items
        self.all_items = items
        self.champion_stats = champion_stats
        self.champ = champion_stats
        self.target = target
        self.level = max(1, min(18, int(champion_level)))
        self.progress_callback = progress_callback
        self.constraints = constraints or {}
        self.role = str(role or "middle").strip().lower()
        self.champion_name = champion_name
        self.profile = get_champion_profile(champion_name)
        self.role_gets_boots_passive = self.role == "middle"

        self.excluded_ids = {int(item_id) for item_id in self.constraints.get("exclude_items", [])}
        self.forced_items = [int(item_id) for item_id in self.constraints.get("force_items", [])]
        self.min_hp = float(self.constraints.get("min_hp", 0) or 0)
        self.prefer_tags = {str(tag).strip() for tag in self.constraints.get("prefer_tags", []) if str(tag).strip()}

        self.boots_pool = [
            item for item in self.items.values()
            if item.get("is_boots") and item["id"] not in self.excluded_ids
        ]
        self.main_pool = [
            item["id"] for item in self.items.values()
            if not item.get("is_boots") and item["id"] not in self.excluded_ids
        ]
        self.mythic_pool = [
            item["id"] for item in self.items.values()
            if item.get("is_mythic") and not item.get("is_boots") and item["id"] not in self.excluded_ids
        ]
        if not self.main_pool:
            self.main_pool = [item["id"] for item in self.items.values() if item["id"] not in self.excluded_ids]

    def optimize(self) -> GAResult:
        population = [self._create_random_build() for _ in range(GA_POPULATION)]
        best_build = list(population[0])
        best_score = self._fitness(best_build)
        best_generation = 0

        for generation in range(GA_GENERATIONS):
            scored = sorted(
                ((self._fitness(build), build) for build in population),
                key=lambda pair: pair[0],
                reverse=True,
            )
            generation_best_score, generation_best_build = scored[0]
            if generation_best_score > best_score:
                best_score = generation_best_score
                best_build = list(generation_best_build)
                best_generation = generation
            if self.progress_callback:
                self.progress_callback(generation + 1, generation_best_score)

            elite_count = max(2, int(GA_POPULATION * GA_ELITE_RATIO))
            next_population = [list(build) for _, build in scored[:elite_count]]
            while len(next_population) < GA_POPULATION:
                parent_a = self._tournament_selection(scored)
                parent_b = self._tournament_selection(scored)
                child = self._crossover(parent_a, parent_b)
                child = self._mutate(child)
                child = self._normalize_build(child)
                next_population.append(child)
            population = next_population

        final_stats = self._aggregate_stats(best_build)
        final_breakdown = self._build_breakdown(final_stats)
        total_gold = sum(int(self.items[item_id].get("gold", 0)) for item_id in best_build if item_id in self.items)
        return GAResult(
            item_ids=best_build,
            fitness=round(best_score, 2),
            target=self.target,
            stats=final_stats,
            breakdown=final_breakdown,
            generation=best_generation + 1,
            generations_run=GA_GENERATIONS,
            total_gold=total_gold,
        )

    def run(self) -> GAResult:
        return self.optimize()

    def _create_random_build(self) -> list[int]:
        build: list[int] = []
        for forced_item in self.forced_items:
            if forced_item in self.items and forced_item not in build:
                build.append(forced_item)
            if len(build) >= BUILD_SIZE:
                break

        mythic_count = sum(1 for item_id in build if self.items.get(item_id, {}).get("is_mythic"))
        if mythic_count == 0 and self.mythic_pool and random.random() > 0.2:
            mythic_choice = random.choice(self.mythic_pool)
            if mythic_choice not in build:
                build.append(mythic_choice)

        attempts = 0
        while len(build) < BUILD_SIZE and attempts < 120:
            pool = self.main_pool + ([] if mythic_count else self.mythic_pool)
            if not pool:
                break
            choice = random.choice(pool)
            item = self.items.get(choice, {})
            if choice in build:
                attempts += 1
                continue
            if item.get("is_mythic") and any(self.items.get(item_id, {}).get("is_mythic") for item_id in build):
                attempts += 1
                continue
            build.append(choice)
            attempts = 0

        return self._normalize_build(build[:BUILD_SIZE])

    def _normalize_build(self, build: list[int]) -> list[int]:
        normalized: list[int] = []
        seen: set[int] = set()
        for item_id in self.forced_items + build:
            if item_id not in self.items or item_id in seen or item_id in self.excluded_ids:
                continue
            normalized.append(item_id)
            seen.add(item_id)

        while len(normalized) < BUILD_SIZE:
            if not self.main_pool:
                break
            choice = random.choice(self.main_pool)
            if choice in seen:
                continue
            normalized.append(choice)
            seen.add(choice)
        return normalized[:BUILD_SIZE]

    def _tournament_selection(self, scored_population: list[tuple[float, list[int]]]) -> list[int]:
        bracket = random.sample(scored_population, min(5, len(scored_population)))
        bracket.sort(key=lambda pair: pair[0], reverse=True)
        return list(bracket[0][1])

    def _crossover(self, parent_a: list[int], parent_b: list[int]) -> list[int]:
        child: list[int] = []
        for idx in range(BUILD_SIZE):
            source = parent_a if random.random() < 0.5 else parent_b
            if idx < len(source):
                child.append(source[idx])
        return child

    def _mutate(self, build: list[int]) -> list[int]:
        mutated = list(build)
        mutable_indices = [index for index, item_id in enumerate(mutated) if item_id not in self.forced_items]
        if not mutable_indices or random.random() >= GA_MUTATION_RATE:
            return mutated

        idx = random.choice(mutable_indices)
        old_item = self.items.get(mutated[idx], {})
        if old_item.get("is_boots"):
            candidates = [item for item in self.boots_pool if item["id"] != mutated[idx]]
            if candidates:
                mutated[idx] = random.choice(candidates)["id"]
        elif old_item.get("is_mythic") and self.mythic_pool:
            candidates = [item_id for item_id in self.mythic_pool if item_id not in mutated or item_id == mutated[idx]]
            if candidates:
                mutated[idx] = random.choice(candidates)
        else:
            has_mythic = any(
                self.items.get(item_id, {}).get("is_mythic")
                for index, item_id in enumerate(mutated)
                if index != idx
            )
            pool = self.main_pool + ([] if has_mythic else self.mythic_pool)
            candidates = [
                item_id for item_id in pool
                if item_id not in mutated or item_id == mutated[idx]
            ]
            if candidates:
                mutated[idx] = random.choice(candidates)
        return mutated

    def _champion_stats_at_level(self) -> dict[str, float]:
        level_scale = self.level - 1
        return {
            "hp": self.champion_stats["hp"] + self.champion_stats["hp_per_level"] * level_scale,
            "armor": self.champion_stats["armor"] + self.champion_stats["armor_per_level"] * level_scale,
            "mr": self.champion_stats["mr"] + self.champion_stats["mr_per_level"] * level_scale,
            "ad": self.champion_stats["ad"] + self.champion_stats["ad_per_level"] * level_scale,
            "as": self.champion_stats["as_base"] * (1 + self.champion_stats["as_ratio"] * level_scale / 100),
            "ap": 0.0,
            "mp": 0.0,
            "ah": 0.0,
            "hp_regen": 0.0,
            "lifesteal": 0.0,
            "ms": self.champion_stats["ms"],
            "ms_pct": 0.0,
            "ap_ratio": self.champion_stats.get("ap_ratio", 0.55),
        }

    def _aggregate_stats(self, item_ids: list[int]) -> dict[str, float]:
        totals = self._champion_stats_at_level()
        for item_id in item_ids:
            item = self.items.get(item_id)
            if not item:
                continue

            item_stats = item.get("stats", {})
            if item.get("is_boots") and not self.role_gets_boots_passive:
                if "ms" in item_stats:
                    totals["ms"] = totals.get("ms", 0.0) + float(item_stats["ms"])
                if "ms_pct" in item_stats:
                    totals["ms_pct"] = totals.get("ms_pct", 0.0) + float(item_stats["ms_pct"])
                    totals["ms"] = totals.get("ms", 0.0) * (1 + float(item_stats["ms_pct"]))
                continue

            for stat_key, value in item_stats.items():
                if stat_key == "as_bonus":
                    totals["as"] = totals.get("as", 0.0) * (1 + float(value))
                elif stat_key == "ms_pct":
                    totals["ms_pct"] = totals.get("ms_pct", 0.0) + float(value)
                    totals["ms"] = totals.get("ms", 0.0) * (1 + float(value))
                else:
                    totals[stat_key] = totals.get(stat_key, 0.0) + float(value)

        totals["crit"] = min(1.0, totals.get("crit", 0.0))
        totals["arpen_pct"] = min(0.45, totals.get("arpen_pct", 0.0))
        totals["mpen_pct"] = min(0.40, totals.get("mpen_pct", 0.0))
        return totals

    def _has_redundant_uniques(self, item_ids: list[int]) -> bool:
        for group in MUTUALLY_EXCLUSIVE_GROUPS:
            if len(group & set(item_ids)) > 1:
                return True

        unique_passive_names: list[str] = []
        for item_id in item_ids:
            desc = str(self.all_items.get(item_id, {}).get("description", ""))
            unique_passive_names.extend(match.strip().lower() for match in UNIQUE_PASSIVE_RE.findall(desc))

        seen: set[str] = set()
        for name in unique_passive_names:
            if name in seen:
                return True
            seen.add(name)
        return False

    def _apply_item_modifiers(self, base_score: float, item_ids: list[int], profile: ChampionItemProfile) -> float:
        multiplier = 1.0
        for item_id in item_ids:
            if item_id in profile.item_synergies:
                multiplier *= profile.item_synergies[item_id]
            if item_id in profile.item_penalties:
                multiplier *= profile.item_penalties[item_id]
        return base_score * multiplier

    def _fitness(self, build: list[int]) -> float:
        if self._has_redundant_uniques(build):
            return -800.0

        stats = self._aggregate_stats(build)
        if stats.get("hp", 0.0) < self.min_hp:
            return -1000.0

        score = self._score_for_target(stats, build, self.target)
        if self.prefer_tags:
            tag_matches = 0
            for item_id in build:
                item_tags = set(self.items.get(item_id, {}).get("tags", []))
                if item_tags & self.prefer_tags:
                    tag_matches += 1
            score += tag_matches * 55.0
        return score

    def _score_for_target(self, stats: dict[str, float], item_ids: list[int], target: str) -> float:
        profile = self.profile
        if target == OptimizationTarget.PHYSICAL_DPS:
            total_ad = stats.get("ad", 0.0)
            crit = stats.get("crit", 0.0)
            attack_speed = stats.get("as", 0.625)
            lifesteal = stats.get("lifesteal", 0.0)

            crit_mult = 1.0 + (0.75 * crit * profile.crit_value_mult)
            raw_dps = total_ad * attack_speed * crit_mult

            if profile.on_hit_value_mult != 1.0:
                on_hit_bonus = (attack_speed - self.champ.get("as_base", 0.625)) * profile.on_hit_value_mult * total_ad * 0.3
                raw_dps += max(0.0, on_hit_bonus)

            lethality = stats.get("lethality", 0.0)
            armor_pen = stats.get("arpen_pct", 0.0)
            effective_armor = max(0.0, 100.0 - lethality) * (1.0 - armor_pen)
            dmg_mult = 100.0 / (100.0 + effective_armor)
            sustain = 1.0 + lifesteal * (0.20 + profile.resource_dependency * 0.1)
            return self._apply_item_modifiers(raw_dps * dmg_mult * sustain, item_ids, profile)

        if target == OptimizationTarget.MAGIC_DPS:
            total_ap = stats.get("ap", 0.0)
            mpen = stats.get("mpen", 0.0)
            mpen_pct = stats.get("mpen_pct", 0.0)
            ap_ratio = stats.get("ap_ratio", 0.55)
            effective_mr = max(0.0, 60.0 - mpen) * (1.0 - mpen_pct)
            dmg_mult = 100.0 / (100.0 + effective_mr)

            rotations = profile.ability_rotations_per_fight
            ability_dmg = total_ap * ap_ratio * rotations
            ah = stats.get("ah", 0.0)
            if profile.resource_dependency > 0:
                ah_factor = 1.0 + min(ah / 100.0, 0.3) * profile.resource_dependency
                ability_dmg *= ah_factor
            return self._apply_item_modifiers(ability_dmg * dmg_mult, item_ids, profile)

        if target == OptimizationTarget.HYBRID_DPS:
            score = (
                self._score_for_target(stats, item_ids, OptimizationTarget.PHYSICAL_DPS) * 0.55
                + self._score_for_target(stats, item_ids, OptimizationTarget.MAGIC_DPS) * 0.45
            )
            return self._apply_item_modifiers(score, item_ids, profile)

        if target == OptimizationTarget.TANK_HP:
            hp = stats.get("hp", 0.0)
            armor = stats.get("armor", 0.0)
            mr = stats.get("mr", 0.0)
            return self._apply_item_modifiers(hp * (1.0 + armor / 100.0) * (1.0 + mr / 100.0), item_ids, profile)

        if target == OptimizationTarget.TANK_ARMOR:
            score = stats.get("hp", 0.0) * (1.0 + stats.get("armor", 0.0) / 100.0)
            return self._apply_item_modifiers(score, item_ids, profile)

        if target == OptimizationTarget.TANK_MR:
            score = stats.get("hp", 0.0) * (1.0 + stats.get("mr", 0.0) / 100.0)
            return self._apply_item_modifiers(score, item_ids, profile)

        if target == OptimizationTarget.UTILITY:
            score = (
                stats.get("ah", 0.0) * (9.0 + profile.resource_dependency * 4.0)
                + stats.get("hp", 0.0) * 0.3
                + stats.get("mp", 0.0) * (0.18 + profile.resource_dependency * 0.08)
                + stats.get("hp_regen", 0.0) * 6.0
                + stats.get("ap", 0.0) * 0.4
            )
            return self._apply_item_modifiers(score, item_ids, profile)

        if target == OptimizationTarget.GOLD_EFFICIENCY:
            gross = (
                stats.get("ad", 0.0) * 32.0
                + stats.get("ap", 0.0) * 20.0
                + stats.get("hp", 0.0) * 2.4
                + stats.get("armor", 0.0) * 18.0
                + stats.get("mr", 0.0) * 18.0
                + stats.get("ah", 0.0) * 22.0
            )
            return self._apply_item_modifiers(gross, item_ids, profile)

        if target == OptimizationTarget.LETHALITY:
            total_ad = stats.get("ad", 0.0)
            lethality = stats.get("lethality", 0.0)
            arpen_pct = stats.get("arpen_pct", 0.0)
            effective_armor = max(0.0, 60.0 - lethality) * (1.0 - arpen_pct)
            dmg_mult = 100.0 / (100.0 + effective_armor)
            score = (total_ad * 2.0 + lethality * 0.8) * dmg_mult
            return self._apply_item_modifiers(score, item_ids, profile)

        if target == OptimizationTarget.LIFESTEAL_DPS:
            dps = self._score_for_target(stats, item_ids, OptimizationTarget.PHYSICAL_DPS)
            score = dps + stats.get("lifesteal", 0.0) * 150.0 + stats.get("hp", 0.0) * 0.15
            return self._apply_item_modifiers(score, item_ids, profile)

        return 0.0

    def _build_breakdown(self, stats: dict[str, float]) -> dict[str, float]:
        return {
            "hp": round(stats.get("hp", 0.0), 1),
            "ad": round(stats.get("ad", 0.0), 1),
            "ap": round(stats.get("ap", 0.0), 1),
            "armor": round(stats.get("armor", 0.0), 1),
            "mr": round(stats.get("mr", 0.0), 1),
            "attack_speed": round(stats.get("as", 0.0), 3),
            "crit": round(stats.get("crit", 0.0) * 100.0, 1),
            "ability_haste": round(stats.get("ah", 0.0), 1),
            "lifesteal": round(stats.get("lifesteal", 0.0) * 100.0, 1),
            "move_speed": round(stats.get("ms", 0.0), 1),
        }
