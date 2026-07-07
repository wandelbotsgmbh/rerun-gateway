"""Plan a robot trajectory with Wandelbots NOVA and stream it to a remote Rerun server.

This example ties together three pieces:

1. **NOVA** (`wandelbots-nova`) — the `@nova.program` decorator declares a *virtual*
   Universal Robots controller as a precondition, so running the program deploys a
   simulated robot into the cell on the fly (no physical hardware needed).
2. **The motion planner** — we plan a small Cartesian trajectory for that robot.
3. **nova-rerun-bridge** — logs the robot model, safety zones, planned actions and the
   resulting joint trajectory to Rerun for 3D visualization.

Unlike the bridge's default behaviour (spawn a local Rerun viewer), we point it at a
**remote** Rerun gRPC server — the `rerun-gateway` app deployed in the cluster. The
bridge logs to the global recording created by `rr.init(application_id="nova", ...)`;
we redirect that recording's sink to the remote server with `rr.connect_grpc(...)`.

Configuration (env vars):
    NOVA_API            Base URL of the NOVA instance, e.g. http://172.31.10.154
    NOVA_ACCESS_TOKEN   Access token (omit for local/unauthenticated instances)
    RERUN_ADDRESS       Rerun gRPC endpoint. Defaults to the in-cluster gateway address
                        (rerun+http://app-rerun-gateway:8080/proxy). From a laptop, point
                        it at a port-forward or the local viewer, e.g.
                        rerun+http://127.0.0.1:9876/proxy

Run:
    uv run plan_and_log.py
"""

import os

import nova
import rerun as rr
from nova import api
from nova.actions import cartesian_ptp, joint_ptp, linear
from nova.cell import virtual_controller
from nova.program import ProgramPreconditions
from nova.types import MotionSettings, Pose
from nova.viewers.utils import extract_collision_setups_from_actions
from nova_rerun_bridge import NovaRerunBridge

# In-cluster pods reach the gateway by its service name; override for local runs.
RERUN_ADDRESS = os.environ.get(
    "RERUN_ADDRESS", "rerun+http://app-rerun-gateway:8080/proxy"
)

CONTROLLER_NAME = "ur10"


@nova.program(
    name="plan_and_log",
    # The precondition is the "decorator dependency": before the program body runs,
    # NOVA ensures a virtual UR10e controller named `ur10` exists in the cell,
    # deploying a simulated robot if it isn't there yet.
    preconditions=ProgramPreconditions(
        controllers=[
            virtual_controller(
                name=CONTROLLER_NAME,
                manufacturer=api.models.Manufacturer.UNIVERSALROBOTS,
                type="universalrobots-ur10e",
            )
        ],
        # Keep the virtual robot around after the run so you can inspect it.
        cleanup_controllers=False,
    ),
)
async def main(ctx):
    # The @nova.program decorator opens the Nova connection for us; take it from ctx
    # (it has already ensured the virtual controller from the preconditions exists).
    nova_client = ctx.nova

    # spawn=False => don't launch a local desktop viewer. Create the bridge FIRST: with
    # spawn=False it normally skips rr.init entirely, but inside the in-cluster VS Code
    # app (VSCODE_PROXY_URI set) its constructor calls rr.init + rr.save("nova.rrd").
    # We then (re)initialize the recording and point its sink at the remote gateway AFTER
    # the bridge, so our connect_grpc wins in every environment. All subsequent
    # bridge.log_* calls stream to the gateway.
    async with NovaRerunBridge(nova_client, spawn=False) as bridge:
        rr.init(application_id="nova", spawn=False)
        print(f"Connecting Rerun recording to {RERUN_ADDRESS}")
        rr.connect_grpc(RERUN_ADDRESS)

        # Set up the default blueprint (view layout) in the viewer.
        await bridge.setup_blueprint()

        cell = nova_client.cell()
        controller = await cell.controller(CONTROLLER_NAME)

        # A controller can host several motion groups; take the first robot.
        async with controller[0] as motion_group:
            await bridge.log_safety_zones(motion_group)

            tcp = "Flange"
            home = await motion_group.tcp_pose(tcp)
            home_joints = await motion_group.joints()

            # A little out-and-back Cartesian move relative to the home pose.
            actions = [
                cartesian_ptp(home),
                linear(target=Pose((100, 0, 0, 0, 0, 0)) @ home),
                linear(target=Pose((100, 100, 0, 0, 0, 0)) @ home),
                linear(target=Pose((0, 100, 0, 0, 0, 0)) @ home),
                cartesian_ptp(home),
                joint_ptp(home_joints),
            ]
            for action in actions:
                action.settings = MotionSettings(tcp_velocity_limit=200)

            print("Planning trajectory...")
            joint_trajectory = await motion_group.plan(actions, tcp)
            print(
                f"Planned trajectory with {len(joint_trajectory.joint_positions)} "
                "sample points."
            )

            # Log the plan: the discrete action waypoints and the dense trajectory.
            await bridge.log_actions(actions)
            await bridge.log_trajectory(
                trajectory=joint_trajectory,
                tcp=tcp,
                motion_group=motion_group,
                collision_setups=extract_collision_setups_from_actions(actions),
            )
            print("Logged trajectory to Rerun. Open the viewer to inspect it.")


if __name__ == "__main__":
    nova.run_program(main)
